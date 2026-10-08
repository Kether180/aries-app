"""Live checks against the real OpenAI API. Skipped unless OPENAI_API_KEY is configured.

Run with `uv run pytest -m llm`. CI runs `-m "not llm"` so these never block a build.
GNews is still faked here: these tests are about the model's behaviour, not the news API.
"""

import pytest

from app.config import settings
from app.schemas import NewsArticle
from app.services import agent as agent_module
from app.services.ai import SourceDocument, analyze_article, answer_question

pytestmark = [pytest.mark.llm, pytest.mark.skipif(not settings.openai_api_key, reason="OPENAI_API_KEY not set")]

SOLAR = NewsArticle(
    url="https://example.com/solar",
    title="City opens new solar farm, cutting energy bills for 20,000 homes",
    description="The 50MW project was completed ahead of schedule and under budget, officials said.",
    content="Residents are expected to save an average of 120 dollars a year.",
)
TESLA_NEWS = [
    NewsArticle(
        url="https://example.com/t1",
        title="Tesla Q3 deliveries fall 13% as competition intensifies",
        description="Analysts had expected a smaller decline; shares dropped 4% in early trading.",
    ),
    NewsArticle(
        url="https://example.com/t2",
        title="Tesla opens new Berlin battery plant creating 3,000 jobs",
        description="The plant will supply cells for European production from next year.",
    ),
    NewsArticle(url="https://example.com/soup", title="Recipe: the best autumn soups", description="Five soups."),
]


def test_analysis_is_grounded_and_consistent():
    analysis = analyze_article(SOLAR)
    assert analysis.sentiment == "positive"
    assert analysis.sentiment_score > 0
    assert "solar" in analysis.summary.lower()


def test_answer_cites_sources_and_admits_gaps():
    sources = [
        SourceDocument(
            title=SOLAR.title, source_name=None, published_at=None, sentiment="positive", summary=SOLAR.description
        )
    ]
    answer = answer_question("What is the news about solar energy?", sources)
    assert answer.cited_sources == [1]
    assert "[1]" in answer.answer

    off_topic = answer_question("Who won the football world cup?", sources)
    assert off_topic.cited_sources == []


def test_agent_searches_then_answers_with_citations(client, monkeypatch):
    monkeypatch.setattr(agent_module, "fetch_news", lambda q, max_results: TESLA_NEWS)
    body = client.post("/api/research", json={"question": "How is Tesla doing this quarter?"}).json()

    tools = [s["tool"] for s in body["steps"]]
    assert tools[0] == "search_news"
    assert "analyze_articles" in tools
    assert body["cited"], "agent should cite at least one source"
    assert all("soup" not in s["title"].lower() for s in body["sources"]), "irrelevant article should be skipped"
