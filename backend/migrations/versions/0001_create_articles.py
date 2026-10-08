"""create articles table

Revision ID: 0001
Revises:
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SEARCH_DOCUMENT = (
    "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' "
    "|| coalesce(summary, '') || ' ' || coalesce(query, ''))"
)


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("source_name", sa.String(255)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("image_url", sa.String(2048)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("query", sa.String(255)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(16), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("sentiment_reason", sa.Text(), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_articles_url", "articles", ["url"], unique=True)
    op.create_index("ix_articles_sentiment", "articles", ["sentiment"])
    op.create_index("ix_articles_created_at", "articles", ["created_at"])

    # Full-text search index for RAG retrieval (Postgres only; must match models.search_document)
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"CREATE INDEX ix_articles_search ON articles USING gin ({SEARCH_DOCUMENT})")


def downgrade() -> None:
    op.drop_table("articles")
