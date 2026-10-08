"""Agent loop tests with a scripted fake model: no network, deterministic tool calls."""

import json
from types import SimpleNamespace

import pytest

from app.schemas import NewsArticle
from app.services import agent as agent_module
from app.services.ai import Analysis, Answer
from app.services.errors import UpstreamError

NEWS = [
    NewsArticle(url="https://ex.com/a", title="Tesla profit falls 20%", description="Margins squeezed."),
    NewsArticle(url="https://ex.com/b", title="Tesla opens new factory", description="Jobs for the region."),
]


def tool_call(name, **args):
    return SimpleNamespace(id=f"call_{name}", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def model_turn(tool_calls=None, parsed=None):
    return SimpleNamespace(tool_calls=tool_calls or [], content=None, parsed=parsed)


@pytest.fixture
def fakes(monkeypatch):
    """Fake GNews and per-article analysis; the model is scripted per test via `script`."""
    monkeypatch.setattr(agent_module, "fetch_news", lambda q, max_results: NEWS)
    monkeypatch.setattr(
        agent_module,
        "analyze_article",
        lambda a: Analysis(
            summary=f"Summary of {a.title}", sentiment="negative", sentiment_score=-0.5, sentiment_reason="r"
        ),
    )
    calls = []

    def script(turns):
        turns = iter(turns)

        def fake_call_model(self, messages, *, first, final):
            calls.append({"first": first, "final": final, "roles": [m["role"] for m in messages]})
            return next(turns)

        monkeypatch.setattr(agent_module.ResearchAgent, "_call_model", fake_call_model)

    script.calls = calls
    return script


def test_agent_searches_analyses_and_cites(client, fakes):
    fakes(
        [
            model_turn([tool_call("search_news", query="Tesla")]),
            model_turn([tool_call("analyze_articles", urls=["https://ex.com/a"])]),
            model_turn(parsed=Answer(answer="Profit fell 20% [1].", cited_sources=[1, 9])),
        ]
    )
    res = client.post("/api/research", json={"question": "How is Tesla doing?"})
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "Profit fell 20% [1]."
    assert body["cited"] == [1]  # citation to non-existent source 9 dropped
    assert [s["tool"] for s in body["steps"]] == ["search_news", "analyze_articles"]
    assert [s["title"] for s in body["sources"]] == ["Tesla profit falls 20%"]
    # First call must use a tool; the model saw tool results before answering
    assert fakes.calls[0]["first"] is True
    assert fakes.calls[2]["roles"] == ["system", "user", "assistant", "tool", "assistant", "tool"]
    # The analysed article is now in the library
    assert client.get("/api/articles").json()["total"] == 1


def test_agent_reuses_already_analysed_articles(client, fakes, monkeypatch):
    from app.routers import articles as articles_router

    monkeypatch.setattr(
        articles_router,
        "analyze_article",
        lambda a: Analysis(summary="stored", sentiment="positive", sentiment_score=0.5, sentiment_reason="r"),
    )
    client.post("/api/articles", json={"url": "https://ex.com/b", "title": "Tesla opens new factory"})

    fakes(
        [
            model_turn([tool_call("search_news", query="Tesla")]),
            model_turn(parsed=Answer(answer="New factory [1].", cited_sources=[1])),
        ]
    )
    body = client.post("/api/research", json={"question": "Tesla?"}).json()
    assert "ALREADY ANALYSED as source [1]" in body["steps"][0]["output"]
    assert body["sources"][0]["summary"] == "stored"
    assert client.get("/api/articles").json()["total"] == 1  # nothing re-analysed


def test_agent_enforces_search_budget(client, fakes):
    fakes(
        [
            model_turn(
                [
                    tool_call("search_news", query="a"),
                    tool_call("search_news", query="b"),
                    tool_call("search_news", query="c"),
                ]
            ),
            model_turn(parsed=Answer(answer="Nothing.", cited_sources=[])),
        ]
    )
    body = client.post("/api/research", json={"question": "anything"}).json()
    assert "budget" in body["steps"][2]["output"]


def test_agent_step_limit_returns_502(client, fakes):
    fakes([model_turn([tool_call("search_news", query="x")])] * agent_module.MAX_STEPS)
    res = client.post("/api/research", json={"question": "loop forever"})
    assert res.status_code == 502
    assert "step budget" in res.json()["detail"]


def test_agent_reports_search_failure_to_model(client, fakes, monkeypatch):
    def boom(q, max_results):
        raise UpstreamError("gnews", "daily request limit reached", 429)

    monkeypatch.setattr(agent_module, "fetch_news", boom)
    fakes(
        [
            model_turn([tool_call("search_news", query="x")]),
            model_turn(parsed=Answer(answer="Search unavailable.", cited_sources=[])),
        ]
    )
    body = client.post("/api/research", json={"question": "anything"}).json()
    assert body["steps"][0]["output"] == "Search failed: daily request limit reached"
    assert body["answer"] == "Search unavailable."


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_stream_sends_steps_then_answer(client, fakes):
    fakes(
        [
            model_turn([tool_call("search_news", query="Tesla")]),
            model_turn([tool_call("analyze_articles", urls=["https://ex.com/a"])]),
            model_turn(parsed=Answer(answer="Profit fell 20% [1].", cited_sources=[1])),
        ]
    )
    res = client.post("/api/research/stream", json={"question": "How is Tesla doing?"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    assert [kind for kind, _ in events] == ["step", "step", "answer"]
    assert events[0][1]["tool"] == "search_news"
    assert events[2][1]["answer"] == "Profit fell 20% [1]."
    assert events[2][1]["cited"] == [1]


def test_stream_reports_upstream_error_as_event(client, fakes, monkeypatch):
    def boom(self, messages, *, first, final):
        raise UpstreamError("openai", "rate limited")

    monkeypatch.setattr(agent_module.ResearchAgent, "_call_model", boom)
    res = client.post("/api/research/stream", json={"question": "anything"})
    assert res.status_code == 200  # the stream itself succeeds; the error is an event
    assert parse_sse(res.text) == [("error", {"detail": "rate limited", "service": "openai"})]
