"""Unit tests for the service layer's parsing and post-processing (no network)."""

from types import SimpleNamespace

import pytest

from app.services import ai, news
from app.services.ai import Analysis, Answer, SourceDocument
from app.services.errors import UpstreamError


def test_gnews_article_mapping():
    raw = {
        "title": "Title",
        "description": "Desc",
        "content": "Body",
        "url": "https://example.com/a",
        "image": "https://example.com/a.jpg",
        "publishedAt": "2026-10-01T12:00:00Z",
        "source": {"name": "Example", "url": "https://example.com"},
    }
    article = news._gnews_article(raw)
    assert article.source_name == "Example"
    assert article.image_url == "https://example.com/a.jpg"
    assert article.published_at.year == 2026


def test_gnews_results_are_cached(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "test-key")
    news._cache.clear()
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        return SimpleNamespace(status_code=200, json=lambda: {"articles": []}, headers={}, text="")

    monkeypatch.setattr(news.httpx, "get", fake_get)
    news.fetch_news("ai")
    news.fetch_news("ai")
    news.fetch_news("climate")
    assert [c["q"] for c in calls] == ["ai", "climate"]


def test_answer_drops_citations_to_missing_sources(monkeypatch):
    monkeypatch.setattr(ai, "_complete", lambda *args: Answer(answer="x [1][7]", cited_sources=[7, 1, 1, 0]))
    source = SourceDocument(title="t", source_name=None, published_at=None, sentiment="neutral", summary="s")
    assert ai.answer_question("q", [source, source]).cited_sources == [1]


def test_missing_inline_markers_are_appended():
    from app.services.ai import finalize_citations

    fixed = finalize_citations(Answer(answer="Rates went up.", cited_sources=[2, 1, 9]), source_count=2)
    assert fixed.answer == "Rates went up. [1][2]"
    assert fixed.cited_sources == [1, 2]

    untouched = finalize_citations(Answer(answer="Rates went up [1].", cited_sources=[1]), source_count=2)
    assert untouched.answer == "Rates went up [1]."

    none = finalize_citations(Answer(answer="No idea.", cited_sources=[]), source_count=2)
    assert none.answer == "No idea."


def test_gnews_retries_once_on_per_second_limit(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "test-key")
    monkeypatch.setattr(news.time, "sleep", lambda s: None)
    news._cache.clear()
    responses = iter(
        [
            SimpleNamespace(status_code=429, json=lambda: {}, headers={}, text="too fast"),
            SimpleNamespace(status_code=200, json=lambda: {"articles": []}, headers={}, text=""),
        ]
    )
    calls = []
    monkeypatch.setattr(news.httpx, "get", lambda url, params, timeout: calls.append(url) or next(responses))
    assert news.fetch_news("retry-me") == []
    assert len(calls) == 2


def test_sentiment_label_follows_score():
    from app.services.ai import reconcile_sentiment

    assert (
        reconcile_sentiment(
            Analysis(summary="s", sentiment="neutral", sentiment_score=-0.6, sentiment_reason="r")
        ).sentiment
        == "negative"
    )
    assert (
        reconcile_sentiment(
            Analysis(summary="s", sentiment="positive", sentiment_score=0.1, sentiment_reason="r")
        ).sentiment
        == "neutral"
    )
    assert (
        reconcile_sentiment(
            Analysis(summary="s", sentiment="negative", sentiment_score=0.5, sentiment_reason="r")
        ).sentiment
        == "positive"
    )


RSS_SAMPLE = """<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
<item><title>Central bank raises rates - Reuters</title><link>https://example.com/rates</link>
<pubDate>Wed, 08 Oct 2026 10:00:00 GMT</pubDate>
<description>&lt;a href="x"&gt;Central bank raises rates&lt;/a&gt;&amp;nbsp;
&lt;font&gt;Reuters&lt;/font&gt;</description>
<source url="https://reuters.com">Reuters</source></item>
<item><title>No link</title></item>
</channel></rss>"""


def test_rss_fallback_when_gnews_is_rate_limited(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "test-key")
    monkeypatch.setattr(news.time, "sleep", lambda s: None)
    news._cache.clear()
    calls = []

    def fake_get(url, params, timeout, follow_redirects=False):
        calls.append(url)
        if url.startswith(news.BASE_URL):
            return SimpleNamespace(status_code=429, json=lambda: {}, headers={}, text="limit")
        return SimpleNamespace(status_code=200, text=RSS_SAMPLE, raise_for_status=lambda: None)

    monkeypatch.setattr(news.httpx, "get", fake_get)
    articles = news.fetch_news("rates", country="gb")
    assert [c.startswith(news.BASE_URL) for c in calls] == [True, True, False]  # GNews, retry, then RSS
    assert len(articles) == 1
    a = articles[0]
    assert a.title == "Central bank raises rates"  # " - Reuters" suffix removed
    assert a.source_name == "Reuters"
    assert a.description is None  # the feed description only repeated the headline and outlet
    assert a.published_at.year == 2026


def test_rss_used_when_no_gnews_key(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "")
    news._cache.clear()
    monkeypatch.setattr(
        news.httpx,
        "get",
        lambda url, params, timeout, follow_redirects=False: SimpleNamespace(
            status_code=200, text=RSS_SAMPLE, raise_for_status=lambda: None
        ),
    )
    assert len(news.fetch_news(None)) == 1


def test_non_rate_limit_gnews_errors_still_raise(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "test-key")
    news._cache.clear()
    monkeypatch.setattr(
        news.httpx,
        "get",
        lambda url, params, timeout, follow_redirects=False: SimpleNamespace(
            status_code=401, json=lambda: {"errors": ["bad key"]}, headers={"content-type": "application/json"}, text=""
        ),
    )
    with pytest.raises(UpstreamError):
        news.fetch_news("x")


def test_rss_fallback_when_gnews_daily_limit_is_a_403(monkeypatch):
    monkeypatch.setattr(news.settings, "gnews_api_key", "test-key")
    news._cache.clear()

    def fake_get(url, params, timeout, follow_redirects=False):
        if url.startswith(news.BASE_URL):
            body = {"errors": ["You have reached your request limit for today, the next reset will be tomorrow"]}
            return SimpleNamespace(
                status_code=403, json=lambda: body, headers={"content-type": "application/json"}, text=str(body)
            )
        return SimpleNamespace(status_code=200, text=RSS_SAMPLE, raise_for_status=lambda: None)

    monkeypatch.setattr(news.httpx, "get", fake_get)
    assert len(news.fetch_news("rates")) == 1  # served by the RSS fallback
