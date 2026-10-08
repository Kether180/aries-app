from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Article
from app.schemas import ArticleCreate, ArticleList, ArticleRead, ErrorResponse, Sentiment, SentimentStats, TopicStats
from app.services import articles as article_service
from app.services.ai import analyze_article

router = APIRouter(prefix="/api/articles", tags=["articles"])

UPSTREAM_ERRORS = {502: {"model": ErrorResponse, "description": "OpenAI request failed"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Article not found"}}


def get_article_or_404(article_id: int, db: Session = Depends(get_db)) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post(
    "",
    response_model=ArticleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Analyse and store an article",
    responses={
        200: {"model": ArticleRead, "description": "Already analysed; stored result returned"},
        **UPSTREAM_ERRORS,
    },
)
def create_article(payload: ArticleCreate, response: Response, db: Session = Depends(get_db)):
    """Summarise the article and score its sentiment with OpenAI, then store it.

    Idempotent per URL: if the article was already analysed, the stored result is
    returned with 200 instead of calling OpenAI again.
    """
    existing = article_service.get_by_url(db, str(payload.url))
    if existing:
        response.status_code = status.HTTP_200_OK
        return existing

    analysis = analyze_article(payload)
    article, created = article_service.create(db, payload, analysis, model=settings.openai_model)
    if not created:
        response.status_code = status.HTTP_200_OK
    return article


@router.get("", response_model=ArticleList, summary="List analysed articles")
def list_articles(
    sentiment: Sentiment | None = None,
    q: str | None = Query(default=None, max_length=200, description="Filter by title, summary or search topic"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total, items = article_service.list_articles(db, sentiment=sentiment, q=q, limit=limit, offset=offset)
    return ArticleList(total=total, items=items)


@router.get("/stats", response_model=SentimentStats, summary="Sentiment breakdown of all analysed articles")
def article_stats(db: Session = Depends(get_db)):
    return article_service.stats(db)


@router.get("/topics", response_model=list[TopicStats], summary="Sentiment breakdown per search topic")
def topic_stats(db: Session = Depends(get_db)):
    return article_service.stats_by_topic(db)


@router.get("/{article_id}", response_model=ArticleRead, responses=NOT_FOUND, summary="Get one analysed article")
def get_article(article: Article = Depends(get_article_or_404)):
    return article


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
    summary="Delete an analysed article",
)
def delete_article(article: Article = Depends(get_article_or_404), db: Session = Depends(get_db)):
    article_service.delete(db, article)
