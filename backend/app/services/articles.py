"""Database access for analysed articles. Routers call these; they never build queries themselves."""

import re
from collections.abc import Sequence

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, search_document
from app.schemas import ArticleCreate, Sentiment, SentimentStats
from app.services.ai import Analysis


def get_by_url(db: Session, url: str) -> Article | None:
    return db.scalar(select(Article).where(Article.url == url))


def get_by_urls(db: Session, urls: list[str]) -> dict[str, Article]:
    return {a.url: a for a in db.scalars(select(Article).where(Article.url.in_(urls)))}


def create(db: Session, payload: ArticleCreate, analysis: Analysis, model: str) -> tuple[Article, bool]:
    """Store an analysed article. Returns (article, created); created is False if the URL already existed."""
    url = str(payload.url)
    article = Article(**payload.model_dump(exclude={"url"}), url=url, **analysis.model_dump(), model=model)
    db.add(article)
    try:
        db.commit()
    except IntegrityError:
        # Another request stored the same URL while we were waiting on OpenAI
        db.rollback()
        return get_by_url(db, url), False
    return article, True


def list_articles(
    db: Session, *, sentiment: Sentiment | None, q: str | None, limit: int, offset: int
) -> tuple[int, Sequence[Article]]:
    stmt = select(Article)
    if sentiment:
        stmt = stmt.where(Article.sentiment == sentiment)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Article.title.ilike(pattern), Article.summary.ilike(pattern), Article.query.ilike(pattern))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Article.created_at.desc(), Article.id.desc()).limit(limit).offset(offset)).all()
    return total, items


def stats(db: Session) -> SentimentStats:
    counts = dict(db.execute(select(Article.sentiment, func.count()).group_by(Article.sentiment)).all())
    average = db.scalar(select(func.avg(Article.sentiment_score)))
    return SentimentStats(
        total=sum(counts.values()),
        positive=counts.get("positive", 0),
        neutral=counts.get("neutral", 0),
        negative=counts.get("negative", 0),
        average_score=round(average, 2) if average is not None else None,
    )


def delete(db: Session, article: Article) -> None:
    db.delete(article)
    db.commit()


# --- Retrieval for RAG -------------------------------------------------------------------

# Only used by the SQLite fallback; Postgres full-text search has its own stopword list
STOPWORDS = {
    "what",
    "whats",
    "about",
    "news",
    "with",
    "from",
    "that",
    "this",
    "have",
    "there",
    "their",
    "which",
    "does",
    "saying",
    "tell",
    "give",
    "know",
    "latest",
    "recent",
    "articles",
    "were",
    "will",
    "been",
    "into",
    "than",
    "they",
    "when",
    "where",
}


def search_relevant(db: Session, question: str, limit: int) -> Sequence[Article]:
    """Saved articles most relevant to `question`, best first.

    Postgres: full-text search over title, description, summary and search topic, ranked with
    ts_rank_cd. Terms are OR-ed so a natural-language question still matches articles that
    mention only some of its words. SQLite (local dev/tests): a simple keyword match.
    """
    if db.get_bind().dialect.name == "postgresql":
        document = search_document()
        # plainto_tsquery stems and drops stopwords, giving 'a' & 'b'; swap & for | to match any term
        tsquery = func.to_tsquery(
            "english", func.replace(cast(func.plainto_tsquery("english", question), Text), "&", "|")
        )
        rank = func.ts_rank_cd(document, tsquery)
        stmt = select(Article).where(document.op("@@")(tsquery)).order_by(rank.desc(), Article.created_at.desc())
        return db.scalars(stmt.limit(limit)).all()

    words = {w for w in re.findall(r"[a-z0-9]{4,}", question.lower()) if w not in STOPWORDS}
    if not words:
        return []
    conditions = [col.ilike(f"%{w}%") for w in words for col in (Article.title, Article.summary, Article.query)]
    matches = db.scalars(select(Article).where(or_(*conditions)).order_by(Article.created_at.desc())).all()

    def hits(a: Article) -> int:
        text = f"{a.title} {a.summary} {a.query or ''}".lower()
        return sum(w in text for w in words)

    return sorted(matches, key=hits, reverse=True)[:limit]


def most_recent(db: Session, limit: int) -> Sequence[Article]:
    return db.scalars(select(Article).order_by(Article.created_at.desc()).limit(limit)).all()
