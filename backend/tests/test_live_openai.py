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


# A small labelled set, including the hard case: bad events written in a neutral journalistic style.
EVAL_SET = [
    (
        "negative",
        "Pentagon orders US military to gear up for Iran strikes",
        "Officials said forces were told to prepare options; a decision on timing has not been made.",
    ),
    (
        "negative",
        "Central bank raises interest rates for a third time this year",
        "The move lifts borrowing costs for households and businesses as inflation stays above target.",
    ),
    (
        "negative",
        "Car plant to close next spring with 1,200 jobs lost",
        "The company said the site was no longer viable; unions called the decision devastating.",
    ),
    (
        "negative",
        "Floods displace thousands as river bursts its banks",
        "Emergency services evacuated several villages overnight; two people are missing.",
    ),
    (
        "positive",
        "New battery factory to create 3,000 jobs in the region",
        "Production is due to start next year, supplying cells for European carmakers.",
    ),
    (
        "positive",
        "Regulator drops investigation into pension funds",
        "The watchdog said it found no wrongdoing and would take no further action.",
    ),
    (
        "neutral",
        "Minister to launch consultation on new rules for AI companies",
        "The eight-week consultation will gather views before any legislation is drafted.",
    ),
    (
        "neutral",
        "Five warming soups to make this autumn",
        "From a classic minestrone to a spiced lentil, these recipes take under an hour.",
    ),
]


def test_sentiment_eval_set_mostly_correct():
    results = []
    for expected, title, description in EVAL_SET:
        got = analyze_article(
            NewsArticle(url=f"https://example.com/{abs(hash(title))}", title=title, description=description)
        )
        results.append((expected, got.sentiment, title))
    wrong = [(e, g, t) for e, g, t in results if e != g]
    labels = {g for _, g, _ in results}
    assert len(wrong) <= 1, f"too many mislabelled: {wrong}"
    assert labels >= {"positive", "negative"}, f"labels collapsed: {labels}"
