import pytest

from app.routers import articles as articles_router
from app.routers import news as news_router
from app.schemas import NewsArticle
from app.services.ai import Analysis
from app.services.errors import UpstreamError

ARTICLE = {
    "url": "https://example.com/story",
    "title": "Local team wins championship",
    "description": "A great day for the city.",
    "content": "The team won 3-1...",
    "source_name": "Example News",
    "published_at": "2026-10-01T12:00:00Z",
    "query": "sports",
}


@pytest.fixture
def fake_ai(monkeypatch):
    calls = []

    def fake(article):
        calls.append(article)
        return Analysis(summary="The team won.", sentiment="positive", sentiment_score=0.8, sentiment_reason="A win.")

    monkeypatch.setattr(articles_router, "analyze_article", fake)
    return calls


def test_create_article_analyses_and_stores(client, fake_ai):
    res = client.post("/api/articles", json=ARTICLE)
    assert res.status_code == 201
    body = res.json()
    assert body["sentiment"] == "positive"
    assert body["summary"] == "The team won."
    assert body["query"] == "sports"
    assert len(fake_ai) == 1

    assert client.get(f"/api/articles/{body['id']}").json()["title"] == ARTICLE["title"]


def test_create_article_is_idempotent_per_url(client, fake_ai):
    first = client.post("/api/articles", json=ARTICLE)
    second = client.post("/api/articles", json=ARTICLE)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(fake_ai) == 1  # OpenAI not called twice


def test_list_filters_and_stats(client, monkeypatch):
    sentiments = iter(["positive", "negative", "negative"])

    def fake(article):
        s = next(sentiments)
        return Analysis(
            summary=f"{s} summary", sentiment=s, sentiment_score=0.5 if s == "positive" else -0.5, sentiment_reason="r"
        )

    monkeypatch.setattr(articles_router, "analyze_article", fake)
    for i in range(3):
        client.post("/api/articles", json={**ARTICLE, "url": f"https://example.com/{i}", "title": f"Story {i}"})

    assert client.get("/api/articles").json()["total"] == 3
    negative = client.get("/api/articles", params={"sentiment": "negative"}).json()
    assert negative["total"] == 2
    assert all(a["sentiment"] == "negative" for a in negative["items"])
    assert client.get("/api/articles", params={"q": "story 0"}).json()["total"] == 1

    stats = client.get("/api/articles/stats").json()
    assert stats == {"total": 3, "positive": 1, "neutral": 0, "negative": 2, "average_score": -0.17}


def test_delete_article(client, fake_ai):
    article_id = client.post("/api/articles", json=ARTICLE).json()["id"]
    assert client.delete(f"/api/articles/{article_id}").status_code == 204
    assert client.get(f"/api/articles/{article_id}").status_code == 404
    assert client.delete(f"/api/articles/{article_id}").status_code == 404


def test_invalid_payload_rejected(client, fake_ai):
    assert client.post("/api/articles", json={"title": "no url"}).status_code == 422
    assert client.post("/api/articles", json={"url": "https://example.com/x", "title": "x" * 1025}).status_code == 422
    assert client.post("/api/articles", json={"url": "https://example.com/x", "title": ""}).status_code == 422
    assert client.get("/api/articles", params={"sentiment": "angry"}).status_code == 422


def test_upstream_error_returns_502(client, monkeypatch):
    def boom(article):
        raise UpstreamError("openai", "rate limited")

    monkeypatch.setattr(articles_router, "analyze_article", boom)
    res = client.post("/api/articles", json=ARTICLE)
    assert res.status_code == 502
    assert res.json() == {"detail": "rate limited", "service": "openai"}


def test_news_search_marks_analysed_articles(client, fake_ai, monkeypatch):
    stored_id = client.post("/api/articles", json=ARTICLE).json()["id"]
    results = [NewsArticle(url=ARTICLE["url"], title="a"), NewsArticle(url="https://example.com/new", title="b")]
    monkeypatch.setattr(news_router, "fetch_news", lambda q, lang, max_results: results)

    body = client.get("/api/news", params={"q": "sports"}).json()
    assert body["query"] == "sports"
    assert body["articles"][0]["analysis"]["id"] == stored_id
    assert body["articles"][1]["analysis"] is None
