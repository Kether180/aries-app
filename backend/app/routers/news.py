from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ErrorResponse, NewsSearchResponse, NewsSearchResult
from app.services import articles as article_service
from app.services.news import fetch_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get(
    "",
    response_model=NewsSearchResponse,
    summary="Search recent news",
    responses={
        429: {"model": ErrorResponse, "description": "GNews daily limit reached"},
        502: {"model": ErrorResponse, "description": "GNews request failed"},
    },
)
def search_news(
    q: str | None = Query(default=None, max_length=200, description="Search terms; omit for top headlines"),
    lang: str = Query(default="en", min_length=2, max_length=2),
    max: int = Query(default=10, ge=1, le=10),
    country: str | None = Query(
        default=None, min_length=2, max_length=2, description="Two-letter country code, e.g. us, gb, de"
    ),
    db: Session = Depends(get_db),
):
    """Search GNews, newest first. Articles that were already analysed include their stored `analysis`."""
    query = q.strip() if q and q.strip() else None
    articles = fetch_news(query, lang=lang, max_results=max, country=country.lower() if country else None)

    analysed = article_service.get_by_urls(db, [str(a.url) for a in articles])
    results = [NewsSearchResult(**a.model_dump(), analysis=analysed.get(str(a.url))) for a in articles]
    return NewsSearchResponse(
        query=query, country=country.lower() if country else None, total=len(results), articles=results
    )
