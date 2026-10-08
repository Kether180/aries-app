from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ArticleRead, ErrorResponse, ResearchRequest, ResearchResponse, ResearchStep
from app.services.agent import ResearchAgent

router = APIRouter(prefix="/api/research", tags=["research"])


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
    result = ResearchAgent(db).run(question)
    return ResearchResponse(
        question=question,
        answer=result.answer,
        steps=[ResearchStep.model_validate(s, from_attributes=True) for s in result.steps],
        sources=[ArticleRead.model_validate(s) for s in result.sources],
        cited=result.cited_sources,
    )
