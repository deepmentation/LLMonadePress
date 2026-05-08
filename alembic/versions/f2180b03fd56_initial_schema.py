"""initial schema

Revision ID: f2180b03fd56
Revises:
Create Date: 2026-05-08 20:31:13.068801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2180b03fd56'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_fetched", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("fingerprint", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "external_id"),
    )

    # Add vector column via raw SQL (pgvector type not available in alembic)
    op.execute("ALTER TABLE items ADD COLUMN embedding vector(1024)")

    op.create_table(
        "editions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("device", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("json_payload", postgresql.JSONB(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "edition_items",
        sa.Column("edition_id", sa.Uuid(), sa.ForeignKey("editions.id"), primary_key=True),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("items.id"), primary_key=True),
        sa.Column("cluster_id", sa.Text(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
    )

    op.create_table(
        "deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("edition_id", sa.Uuid(), sa.ForeignKey("editions.id"), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("deliveries")
    op.drop_table("edition_items")
    op.drop_table("editions")
    op.drop_table("items")
    op.drop_table("sources")
    op.execute("DROP EXTENSION IF EXISTS vector")
