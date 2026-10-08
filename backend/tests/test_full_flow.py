"""The whole user journey through the API, in one test.

search -> analyse one -> analyse the rest -> list and filter -> stats -> ask the library
-> research agent -> delete.

`test_full_flow_mocked` runs in CI with GNews and OpenAI faked. `test_full_flow_live` is the same
journey against the real APIs (marked `llm`, skipped without keys; uses 1 GNews request).
"""

import pytest

from app.config import settings
from app.routers import articles as articles_router
from app.routers import ask as ask_router
from app.routers import news as news_router
from app.schemas import NewsArticle
from app.services import agent as agent_module
from app.services import news as news_module
from app.services.ai import Analysis, Answer

FAKE_NEWS = [
    NewsArticle(
        url="https://ex.com/1",
        title="Central bank raises rates to 5%",
        description="Mortgages get dearer.",
        source_name="Reuters",
    ),
    NewsArticle(
        url="https://ex.com/2",
        title="Markets rally on hopes of rate cuts",
        description="Stocks rose sharply.",
        source_name="Bloomberg",
    ),
    NewsArticle(
        url="https://ex.com/3",
        title="New solar farm powers 20,000 homes",
        description="Finished early.",
        source_name="BBC",
    ),
]


def run_flow(client, query: str, max_results: int) -> None:
    # 1. Search: nothing analysed yet
    res = client.get("/api/news", params={"q": query, "max": max_results})
    assert res.status_code == 200, res.text
    found = res.json()["articles"]
    assert found, "search returned no articles"
    assert all(a["analysis"] is None for a in found)

    # 2. Analyse the first article, then post it again: second call must reuse the stored result
    first = {k: v for k, v in found[0].items() if k != "analysis"} | {"query": query}
    created = client.post("/api/articles", json=first)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["sentiment"] in {"positive", "neutral", "negative"}
    assert -1 <= body["sentiment_score"] <= 1
    assert body["summary"] and body["sentiment_reason"]
    again = client.post("/api/articles", json=first)
    assert again.status_code == 200
    assert again.json()["id"] == body["id"]

    # 3. Search again: the analysed article now carries its analysis
    res = client.get("/api/news", params={"q": query, "max": max_results}).json()
    assert res["articles"][0]["analysis"]["id"] == body["id"]

    # 4. Analyse the rest
    for article in found[1:]:
        payload = {k: v for k, v in article.items() if k != "analysis"} | {"query": query}
        assert client.post("/api/articles", json=payload).status_code == 201

    # 5. List, filter, fetch one, stats
    listing = client.get("/api/articles").json()
    assert listing["total"] == len(found)
    assert client.get("/api/articles", params={"q": query}).json()["total"] == len(found)
    one = client.get(f"/api/articles/{body['id']}")
    assert one.status_code == 200 and one.json()["title"] == found[0]["title"]
    stats = client.get("/api/articles/stats").json()
    assert stats["total"] == len(found)
    assert stats["positive"] + stats["neutral"] + stats["negative"] == len(found)

    # 6. Ask the library
    asked = client.post("/api/ask", json={"question": f"What is the news saying about {query}?"})
    assert asked.status_code == 200, asked.text
    assert asked.json()["answer"]
    assert asked.json()["sources"]

    # 7. Research agent: must search, and end with an answer
    researched = client.post("/api/research", json={"question": f"What is happening with {query}?"})
    assert researched.status_code == 200, researched.text
    tools = [s["tool"] for s in researched.json()["steps"]]
    assert tools and tools[0] == "search_news"
    assert researched.json()["answer"]

    # 8. Delete one; it is gone
    assert client.delete(f"/api/articles/{body['id']}").status_code == 204
    assert client.get(f"/api/articles/{body['id']}").status_code == 404
    assert client.get("/api/articles").json()["total"] >= len(found) - 1


def test_full_flow_mocked(client, monkeypatch):
    monkeypatch.setattr(news_module.settings, "gnews_api_key", "test-key")
    monkeypatch.setattr(
        news_router, "fetch_news", lambda q, lang="en", max_results=10, country=None: FAKE_NEWS[:max_results]
    )
    monkeypatch.setattr(agent_module, "fetch_news", lambda q, max_results=5: FAKE_NEWS)

    monkeypatch.setattr(
        articles_router,
        "analyze_article",
        lambda a: Analysis(
            summary=f"Summary of {a.title}", sentiment="neutral", sentiment_score=0.0, sentiment_reason="r"
        ),
    )
    monkeypatch.setattr(agent_module, "analyze_article", articles_router.analyze_article)
    monkeypatch.setattr(ask_router, "answer_question", lambda q, s: Answer(answer="Rates rose [1].", cited_sources=[1]))

    # Scripted agent: search, analyse one, answer
    from types import SimpleNamespace

    turns = iter(
        [
            SimpleNamespace(
                tool_calls=[
                    SimpleNamespace(
                        id="c1", function=SimpleNamespace(name="search_news", arguments='{"query": "rates"}')
                    )
                ],
                content=None,
                parsed=None,
            ),
            SimpleNamespace(
                tool_calls=[
                    SimpleNamespace(
                        id="c2",
                        function=SimpleNamespace(name="analyze_articles", arguments='{"urls": ["https://ex.com/1"]}'),
                    )
                ],
                content=None,
                parsed=None,
            ),
            SimpleNamespace(tool_calls=[], content=None, parsed=Answer(answer="Rates are up [1].", cited_sources=[1])),
        ]
    )
    monkeypatch.setattr(agent_module.ResearchAgent, "_call_model", lambda self, m, *, first, final: next(turns))

    run_flow(client, query="rates", max_results=3)


@pytest.mark.llm
@pytest.mark.skipif(
    not (settings.openai_api_key and settings.gnews_api_key), reason="needs OPENAI_API_KEY and GNEWS_API_KEY"
)
def test_full_flow_live(client):
    """Same journey against the real GNews and OpenAI APIs. Costs 1 GNews request and ~6 OpenAI calls."""
    run_flow(client, query="renewable energy", max_results=3)
