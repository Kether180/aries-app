from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, String, Text, func, literal_column
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Article(Base):
    """A news article that has been analysed. One row per unique article URL."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Article data, as returned by the news API
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    query: Mapped[str | None] = mapped_column(String(255))  # search that surfaced it

    # AI analysis
    summary: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String(16), index=True)  # positive | neutral | negative
    sentiment_score: Mapped[float] = mapped_column(Float)  # -1.0 .. 1.0
    sentiment_reason: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# The text-search configuration must be a SQL literal, not a bound parameter: it is part of an
# index definition (DDL), and Postgres needs a regconfig there.
TS_CONFIG = literal_column("'english'")


def search_document():
    """Postgres full-text search vector for an article, used for RAG retrieval.

    The GIN index below is built on this exact expression, so queries using it are indexed.
    """
    text = (
        func.coalesce(Article.title, "")
        + " "
        + func.coalesce(Article.description, "")
        + " "
        + func.coalesce(Article.summary, "")
        + " "
        + func.coalesce(Article.query, "")
    )
    return func.to_tsvector(TS_CONFIG, text)


Index("ix_articles_search", search_document(), postgresql_using="gin").ddl_if(dialect="postgresql")
