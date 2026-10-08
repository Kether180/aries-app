import pytest

from app.routers import articles as articles_router
from app.routers import ask as ask_router
from app.services.ai import Analysis, Answer

STORIES = [
    (
        "https://example.com/rates",
        "Central bank raises interest rates again",
        "The bank lifted rates to curb inflation.",
        "negative",
    ),
    (
        "https://example.com/solar",
        "City opens record solar farm",
        "A new solar farm will power 20,000 homes.",
        "positive",
    ),
    (
        "https://example.com/chess",
        "Teenager wins national chess title",
        "A 15-year-old won the national championship.",
        "positive",
    ),
]


@pytest.fixture
def library(client, monkeypatch):
    summaries = iter(STORIES)

    def fake_analysis(article):
        _, _, summary, sentiment = next(summaries)
        return Analysis(summary=summary, sentiment=sentiment, sentiment_score=0.5, sentiment_reason="r")

    monkeypatch.setattr(articles_router, "analyze_article", fake_analysis)
    for url, title, _, _ in STORIES:
        client.post("/api/articles", json={"url": url, "title": title})


@pytest.fixture
def fake_answer(monkeypatch):
    seen = {}

    def fake(question, sources):
        seen["titles"] = [s.title for s in sources]
        return Answer(answer="Rates went up [1].", cited_sources=[1])

    monkeypatch.setattr(ask_router, "answer_question", fake)
    return seen


def test_ask_retrieves_relevant_articles(client, library, fake_answer):
    res = client.post("/api/ask", json={"question": "What is happening with interest rates?"})
    assert res.status_code == 200
    body = res.json()
    assert body["retrieval"] == "search"
    assert body["sources"][0]["title"] == "Central bank raises interest rates again"
    assert "City opens record solar farm" not in fake_answer["titles"]
    assert body["answer"] == "Rates went up [1]."
    assert body["cited"] == [1]


def test_ask_falls_back_to_recent_articles(client, library, fake_answer):
    body = client.post("/api/ask", json={"question": "zzz qqq"}).json()
    assert body["retrieval"] == "recent"
    assert len(body["sources"]) == 3


def test_ask_with_empty_library_skips_openai(client, fake_answer):
    body = client.post("/api/ask", json={"question": "Anything new?"}).json()
    assert body["retrieval"] == "empty"
    assert body["sources"] == []
    assert fake_answer == {}  # model never called


def test_ask_validates_question(client):
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 422
