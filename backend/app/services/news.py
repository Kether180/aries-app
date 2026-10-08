"""GNews client (https://gnews.io/docs/v4).

The free tier allows 100 requests/day, so identical requests are cached in memory.
"""

import logging
import time

import httpx

from app.config import settings
from app.schemas import NewsArticle
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

BASE_URL = "https://gnews.io/api/v4"
RETRY_AFTER_SECONDS = 1.2

_cache: dict[tuple, tuple[float, list[NewsArticle]]] = {}


def fetch_news(query: str | None, lang: str = "en", max_results: int = 10) -> list[NewsArticle]:
    """Search articles for `query`, or return top headlines when no query is given."""
    key = (query, lang, max_results)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < settings.news_cache_seconds:
        return cached[1]

    if not settings.gnews_api_key:
        raise UpstreamError("gnews", "GNEWS_API_KEY is not configured", 503)

    params = {"lang": lang, "max": max_results, "apikey": settings.gnews_api_key}
    if query:
        endpoint = "search"
        params["q"] = query
        params["sortby"] = "publishedAt"
    else:
        endpoint = "top-headlines"

    try:
        response = httpx.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
        if response.status_code == 429:
            # The free tier also allows only 1 request per second. One short retry covers a user
            # clicking a topic right after the page loaded; the daily limit still surfaces as 429.
            time.sleep(RETRY_AFTER_SECONDS)
            response = httpx.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
    except httpx.HTTPError as exc:
        logger.warning("GNews request failed: %s", exc)
        raise UpstreamError("gnews", f"request failed: {exc}") from exc

    if response.status_code != 200:
        logger.warning("GNews returned HTTP %s: %s", response.status_code, response.text[:200])
    if response.status_code == 429:
        raise UpstreamError(
            "gnews", "GNews rate limit reached (free tier: 100 requests a day, 1 per second). Try again shortly.", 429
        )
    if response.status_code != 200:
        errors = (
            response.json().get("errors")
            if response.headers.get("content-type", "").startswith("application/json")
            else None
        )
        raise UpstreamError("gnews", f"HTTP {response.status_code}: {errors or response.text[:200]}")

    articles = [_to_article(raw) for raw in response.json().get("articles", [])]
    logger.info("GNews %s %r -> %d articles", endpoint, query, len(articles))
    _cache[key] = (time.monotonic(), articles)
    return articles


def _to_article(raw: dict) -> NewsArticle:
    source = raw.get("source") or {}
    return NewsArticle(
        url=raw["url"],
        title=raw["title"],
        description=raw.get("description"),
        content=raw.get("content"),
        source_name=source.get("name"),
        source_url=source.get("url"),
        image_url=raw.get("image"),
        published_at=raw.get("publishedAt"),
    )
