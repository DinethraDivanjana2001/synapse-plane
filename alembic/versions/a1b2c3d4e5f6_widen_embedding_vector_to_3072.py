"""Widen memory_embeddings.embedding from 1536 to 3072 dimensions

gemini-embedding-001 (the real embedding model this project now uses —
verified with a real call) outputs 3072 dimensions, not the 1536 the initial
schema assumed for OpenAI's text-embedding-3-small. This column is empty in
every fresh deployment (memories are always re-seeded), so a drop-and-recreate
is safe here — a production system with real historical vectors would need a
re-embedding backfill instead of a bare ALTER.

Revision ID: a1b2c3d4e5f6
Revises: e5f4c2125a3d
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e5f4c2125a3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows use the old 1536-dim vectors and would violate the new
    # NOT NULL column with no way to backfill a value of a different
    # dimension — safe to clear here since demo/seed.py re-populates this
    # table (with real values) on every container start regardless.
    op.execute("DELETE FROM memory_embeddings")
    op.drop_column("memory_embeddings", "embedding")
    op.add_column(
        "memory_embeddings",
        sa.Column("embedding", Vector(3072), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("memory_embeddings", "embedding")
    op.add_column(
        "memory_embeddings",
        sa.Column("embedding", Vector(1536), nullable=False),
    )
