import json
import logging
import queue
import threading
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ArticleRead, ErrorResponse, ResearchRequest, ResearchResponse, ResearchStep
from app.services.agent import AgentStep, ResearchAgent, ResearchResult
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


def to_response(question: str, result: ResearchResult) -> ResearchResponse:
    return ResearchResponse(
        question=question,
        answer=result.answer,
        steps=[ResearchStep.model_validate(s, from_attributes=True) for s in result.steps],
        sources=[ArticleRead.model_validate(s) for s in result.sources],
        cited=result.cited_sources,
    )


@router.post(
    "",
    response_model=ResearchResponse,
    summary="Research a question with the news agent",
    responses={502: {"model": ErrorResponse, "description": "OpenAI or GNews request failed"}},
)
def research(payload: ResearchRequest, db: Session = Depends(get_db)):
    """Agentic research: the model searches the news, analyses relevant articles (which are stored,
    so they appear in the library), then answers with citations. Returns the steps it took.
    """
    question = payload.question.strip()
    return to_response(question, ResearchAgent(db).run(question))


@router.post(
    "/stream",
    summary="Research a question, streaming each step as it happens (server-sent events)",
    responses={200: {"content": {"text/event-stream": {}}, "description": "Events: step, answer, error"}},
)
def research_stream(payload: ResearchRequest, db: Session = Depends(get_db)):
    """Same as POST /api/research, but as a text/event-stream so the UI can show progress.

    Events: `step` (one per tool call, same shape as ResearchStep), then either `answer`
    (the full ResearchResponse) or `error` ({detail, service}).
    """
    question = payload.question.strip()
    return StreamingResponse(
        _events(question, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _events(question: str, db: Session) -> Iterator[str]:
    # The agent runs in a worker thread and pushes events into a queue; this generator drains it,
    # so each step reaches the client as soon as the tool finishes rather than at the end.
    events: queue.Queue[tuple[str, dict] | None] = queue.Queue()

    def on_step(step: AgentStep) -> None:
        events.put(("step", step.model_dump()))

    def worker() -> None:
        try:
            result = ResearchAgent(db, on_step=on_step).run(question)
            events.put(("answer", to_response(question, result).model_dump(mode="json")))
        except UpstreamError as exc:
            events.put(("error", {"detail": exc.message, "service": exc.service}))
        except Exception:
            logger.exception("research stream failed")
            events.put(("error", {"detail": "Internal server error"}))
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()
    while (item := events.get()) is not None:
        kind, data = item
        yield f"event: {kind}\ndata: {json.dumps(data)}\n\n"
