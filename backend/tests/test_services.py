"""Unit tests for the service layer's parsing and post-processing (no network)."""

from types import SimpleNamespace

from app.services import ai, news
from app.services.ai import Answer, SourceDocument


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
    article = news._to_article(raw)
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
