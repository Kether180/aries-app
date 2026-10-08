"""OpenAI calls: per-article analysis, and question answering over saved articles (RAG).

Both use structured outputs, so responses are validated against a Pydantic model.
"""

import logging
import re
import time
from collections.abc import Sequence
from functools import lru_cache

import openai
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas import NewsArticle, Sentiment
from app.services.errors import UpstreamError

logger = logging.getLogger(__name__)


@lru_cache
def _client() -> openai.OpenAI:
    return openai.OpenAI(api_key=settings.openai_api_key, timeout=30, max_retries=2)


def _complete[T: BaseModel](system: str, user: str, schema: type[T]) -> T:
    if not settings.openai_api_key:
        raise UpstreamError("openai", "OPENAI_API_KEY is not configured", 503)

    started = time.perf_counter()
    try:
        completion = _client().chat.completions.parse(
            model=settings.openai_model,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
        )
    except openai.OpenAIError as exc:
        logger.warning("OpenAI request failed: %s", exc)
        raise UpstreamError("openai", str(exc)) from exc

    result = completion.choices[0].message.parsed
    usage = completion.usage
    logger.info(
        "OpenAI %s in %.1fs (%s tokens)",
        schema.__name__,
        time.perf_counter() - started,
        usage.total_tokens if usage else "?",
    )
    if result is None:
        raise UpstreamError("openai", "model returned no answer (refusal or invalid output)")
    return result


# --- Article analysis --------------------------------------------------------------------

ANALYSIS_PROMPT = """You are a news analyst. Given a news article, produce:
- summary: 2-3 neutral, factual sentences covering who, what and why it matters.
- sentiment: is the NEWS good, bad or neither for the people and organisations the article is
  mainly about? This is about the event, not the writing. News reporting is almost always
  written in a neutral style; the events it describes usually are not. Decide in three steps:
  1. Who is mainly affected?
  2. What happened to them, or what is likely to happen?
  3. Good for them: positive. Bad for them: negative. Only when nothing good or bad happens
     (a plain announcement, an explainer, a how-to, routine updates) or the good and bad
     genuinely balance out: neutral.
  Examples: "Factory closes, 500 jobs lost" is negative. "Plant opens, 3,000 jobs created" is
  positive. "Central bank raises rates again" is negative (costlier borrowing). "Military told
  to prepare strikes" is negative (conflict). "Regulator drops charges against funds" is
  positive for the funds. "How to make autumn soups" is neutral. "Minister to consult on new
  AI rules" is neutral.
- sentiment_score: from -1.0 (clearly bad news) to 1.0 (clearly good news). Use the magnitude
  for how clear it is: 0.7 or more for unmistakable, 0.3 to 0.6 for likely, under 0.3 only for
  faint. Neutral is between -0.2 and 0.2. Do not use exactly 0 unless there is truly no direction.
- sentiment_reason: one short sentence saying who is affected and why it is good or bad for them.
Write the summary and the reason in English, whatever language the article is in.
Only use information in the article. The text may be truncated; do not invent details."""


class Analysis(BaseModel):
    summary: str
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1, le=1)
    sentiment_reason: str


NEUTRAL_BAND = 0.2


def reconcile_sentiment(analysis: Analysis) -> Analysis:
    """Keep the label and the score consistent: the score decides the label when they disagree."""
    score = analysis.sentiment_score
    if abs(score) < NEUTRAL_BAND:
        analysis.sentiment = "neutral"
    else:
        analysis.sentiment = "positive" if score > 0 else "negative"
    return analysis


def analyze_article(article: NewsArticle) -> Analysis:
    text = "\n".join(
        f"{label}: {value}"
        for label, value in [
            ("Title", article.title),
            ("Source", article.source_name),
            ("Published", article.published_at),
            ("Description", article.description),
            ("Content", article.content),
        ]
        if value
    )
    return reconcile_sentiment(_complete(ANALYSIS_PROMPT, text, Analysis))


# --- Question answering over saved articles (RAG) ----------------------------------------

ANSWER_PROMPT = """You answer questions about news using ONLY the numbered sources provided.
- Be concise: 2-5 sentences, plain prose.
- End every sentence that uses a source with its number in square brackets, \
e.g. "Rates rose to 5% [1]." or "Analysts expect cuts [2][3]." Never write a factual sentence without one.
- When it helps, mention how coverage leans (each source has a sentiment label).
- Ignore sources that are not relevant to the question.
- If no source answers the question, say so plainly instead of guessing, and cite nothing.
- cited_sources: the numbers of every source you cited in the answer."""


class Answer(BaseModel):
    answer: str
    cited_sources: list[int]


def finalize_citations(answer: Answer, source_count: int) -> Answer:
    """Keep citations consistent with the sources: drop numbers that point at no source, and if the
    model listed sources but wrote no inline [n] markers (the small model sometimes skips them),
    append them so the reader can see what the answer rests on."""
    answer.cited_sources = sorted({n for n in answer.cited_sources if 1 <= n <= source_count})
    if answer.cited_sources and not re.search(r"\[\d+\]", answer.answer):
        answer.answer = answer.answer.rstrip() + " " + "".join(f"[{n}]" for n in answer.cited_sources)
    return answer


class SourceDocument(BaseModel):
    """What the model sees for each retrieved article."""

    title: str
    source_name: str | None
    published_at: object | None
    sentiment: str
    summary: str


def answer_question(question: str, sources: Sequence[SourceDocument]) -> Answer:
    context = "\n\n".join(
        f"[{n}] {s.title}\n"
        f"Source: {s.source_name or 'unknown'} | Published: {s.published_at or 'unknown'} | Sentiment: {s.sentiment}\n"
        f"Summary: {s.summary}"
        for n, s in enumerate(sources, start=1)
    )
    answer = _complete(ANSWER_PROMPT, f"Sources:\n\n{context}\n\nQuestion: {question}", Answer)
    return finalize_citations(answer, len(sources))
