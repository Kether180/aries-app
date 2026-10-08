from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ArticleRead, AskRequest, AskResponse, ErrorResponse
from app.services import articles as article_service
from app.services.ai import SourceDocument, answer_question

router = APIRouter(prefix="/api/ask", tags=["ask"])

MAX_SOURCES = 6


@router.post(
    "",
    response_model=AskResponse,
    summary="Ask a question about your analysed articles",
    responses={502: {"model": ErrorResponse, "description": "OpenAI request failed"}},
)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    """Retrieval-augmented answer over the library.

    1. Retrieve the saved articles most relevant to the question (full-text search).
    2. If nothing matches, fall back to the most recent articles (e.g. "what's the overall mood?").
    3. Ask the model to answer only from those articles, citing them as [1], [2], ...

    Nothing is stored; this is a computation over existing articles, hence POST rather than a resource.
    """
    question = payload.question.strip()
    sources = article_service.search_relevant(db, question, limit=MAX_SOURCES)
    retrieval = "search"
    if not sources:
        sources = article_service.most_recent(db, limit=MAX_SOURCES)
        retrieval = "recent"
    if not sources:
        return AskResponse(
            question=question,
            answer="Your library is empty. Analyse a few articles first, then ask about them.",
            retrieval="empty",
            sources=[],
            cited=[],
        )

    answer = answer_question(question, [SourceDocument.model_validate(s, from_attributes=True) for s in sources])
    return AskResponse(
        question=question,
        answer=answer.answer,
        retrieval=retrieval,
        sources=[ArticleRead.model_validate(s) for s in sources],
        cited=answer.cited_sources,
    )
