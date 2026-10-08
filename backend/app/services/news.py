"""News search: GNews (https://gnews.io/docs/v4) with a Google News RSS fallback.

GNews gives richer results (description, image, content) but the free tier allows 100 requests a
day and 1 per second. When it is rate limited or no key is configured, the same search is served
from Google News RSS, which needs no key and has no quota but returns no images or body text.
Identical requests are cached in memory for a few minutes either way.
"""

import html
import logging
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from app.config import settings
from app.schemas import NewsArticle
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)

BASE_URL = "https://gnews.io/api/v4"
RSS_URL = "https://news.google.com/rss"
RETRY_AFTER_SECONDS = 1.2

_cache: dict[tuple, tuple[float, list[NewsArticle]]] = {}


def fetch_news(
    query: str | None, lang: str = "en", max_results: int = 10, country: str | None = None
) -> list[NewsArticle]:
    """Search articles for `query`, or return top headlines when no query is given.

    `country` narrows results to one country's press (two-letter codes, e.g. "us", "gb", "de").
    """
    key = (query, lang, max_results, country)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < settings.news_cache_seconds:
        return cached[1]

    if settings.gnews_api_key:
        try:
            articles = _fetch_gnews(query, lang, max_results, country)
        except UpstreamError as exc:
            if exc.status_code != 429:
                raise
            logger.warning("GNews rate limited, falling back to Google News RSS")
            articles = _fetch_rss(query, lang, max_results, country)
    else:
        logger.info("GNEWS_API_KEY not set, using Google News RSS")
        articles = _fetch_rss(query, lang, max_results, country)

    _cache[key] = (time.monotonic(), articles)
    return articles


# --- GNews ----------------------------------------------------------------------------------


def _fetch_gnews(query: str | None, lang: str, max_results: int, country: str | None) -> list[NewsArticle]:
    params: dict[str, str | int] = {"lang": lang, "max": max_results, "apikey": settings.gnews_api_key}
    if country:
        params["country"] = country
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
    # Per-second limit is a 429; the daily limit comes back as a 403 with a "request limit" message
    daily_limit = response.status_code == 403 and "request limit" in response.text.lower()
    if response.status_code == 429 or daily_limit:
        raise UpstreamError(
            "gnews", "GNews rate limit reached (free tier: 100 requests a day, 1 per second). Try again shortly.", 429
        )
    if response.status_code != 200:
        is_json = response.headers.get("content-type", "").startswith("application/json")
        errors = response.json().get("errors") if is_json else None
        raise UpstreamError("gnews", f"HTTP {response.status_code}: {errors or response.text[:200]}")

    articles = [_gnews_article(raw) for raw in response.json().get("articles", [])]
    logger.info("GNews %s %r -> %d articles", endpoint, query, len(articles))
    return articles


def _gnews_article(raw: dict) -> NewsArticle:
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


# --- Google News RSS (no key, no quota) ---------------------------------------------------


def _fetch_rss(query: str | None, lang: str, max_results: int, country: str | None) -> list[NewsArticle]:
    cc = (country or "us").upper()
    params = {"hl": f"{lang}-{cc}", "gl": cc, "ceid": f"{cc}:{lang}"}
    if query:
        url = f"{RSS_URL}/search"
        params["q"] = query
    else:
        url = RSS_URL
    try:
        response = httpx.get(url, params=params, timeout=10, follow_redirects=True)
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except (httpx.HTTPError, ET.ParseError) as exc:
        logger.warning("Google News RSS failed: %s", exc)
        raise UpstreamError("gnews", f"news feed unavailable: {exc}") from exc

    articles = [a for a in (_rss_article(item) for item in root.iter("item")) if a is not None]
    logger.info("Google News RSS %r -> %d articles", query, len(articles))
    return articles[:max_results]


_TAGS = re.compile(r"<[^>]+>")


def _rss_article(item: ET.Element) -> NewsArticle | None:
    link = item.findtext("link") or ""
    title = item.findtext("title") or ""
    if not link or not title:
        return None
    source = item.find("source")
    source_name = source.text if source is not None else None
    # Google appends " - Source" to titles; drop it when it matches the source element
    if source_name and title.endswith(f" - {source_name}"):
        title = title[: -len(source_name) - 3]
    text = html.unescape(_TAGS.sub(" ", item.findtext("description") or ""))
    description = re.sub(r"\s+", " ", text).strip() or None  # also collapses &nbsp;
    # Google's description is usually just the headline plus the outlet name: no use repeating it
    if description and description.lower().startswith(title.strip().lower()):
        description = None
    published = item.findtext("pubDate")
    try:
        published_at = parsedate_to_datetime(published) if published else None
    except (TypeError, ValueError):
        published_at = None
    return NewsArticle(
        url=link,
        title=title.strip(),
        description=description,
        source_name=source_name,
        source_url=source.get("url") if source is not None else None,
        published_at=published_at,
    )
