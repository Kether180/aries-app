from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Sentiment = Literal["positive", "neutral", "negative"]


class NewsArticle(BaseModel):
    """An article from the news API, before (or regardless of) analysis.

    Length limits match the database columns, so oversized input is a 422, not a database error.
    """

    url: HttpUrl = Field(max_length=2048)
    title: str = Field(min_length=1, max_length=1024)
    description: str | None = None
    content: str | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    image_url: str | None = Field(default=None, max_length=2048)
    published_at: datetime | None = None


class ArticleCreate(NewsArticle):
    query: str | None = Field(default=None, max_length=255)


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    description: str | None
    content: str | None
    source_name: str | None
    source_url: str | None
    image_url: str | None
    published_at: datetime | None
    query: str | None
    summary: str
    sentiment: Sentiment
    sentiment_score: float
    sentiment_reason: str
    model: str
    created_at: datetime


class ArticleList(BaseModel):
    total: int
    items: list[ArticleRead]


class SentimentStats(BaseModel):
    total: int
    positive: int
    neutral: int
    negative: int
    average_score: float | None


class TopicStats(SentimentStats):
    topic: str  # the search that surfaced the articles


class NewsSearchResult(NewsArticle):
    # The stored analysis when this article was already analysed, so the UI can show it
    # straight away instead of calling OpenAI again
    analysis: ArticleRead | None = None


class NewsSearchResponse(BaseModel):
    query: str | None
    country: str | None = None
    total: int
    articles: list[NewsSearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    question: str
    answer: str
    # How sources were picked: "search" = relevant to the question; "recent" = no match,
    # so the newest articles were used; "empty" = library has no articles yet
    retrieval: Literal["search", "recent", "empty"]
    sources: list[ArticleRead]  # numbered [1]..[n] in the answer, in this order
    cited: list[int]  # source numbers the answer actually cites


class ErrorResponse(BaseModel):
    detail: str
    service: str | None = None  # set when a third-party API (gnews / openai) failed


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)


class ResearchStepItem(BaseModel):
    url: str
    title: str
    source_name: str | None = None
    status: Literal["found", "already_analysed", "analysed", "skipped"]
    sentiment: Sentiment | None = None
    source_number: int | None = None  # the [n] used in the answer, once analysed
    note: str | None = None


class ResearchStep(BaseModel):
    tool: str
    input: dict
    output: str  # raw tool result as the model saw it
    items: list[ResearchStepItem] = []  # the same information, structured for display


class ResearchResponse(BaseModel):
    question: str
    answer: str
    steps: list[ResearchStep]  # what the agent did, in order
    sources: list[ArticleRead]  # numbered [1]..[n] in the answer, in this order
    cited: list[int]
