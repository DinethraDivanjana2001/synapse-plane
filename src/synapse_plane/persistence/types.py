"""Dialect-aware embedding column: real pgvector on Postgres, JSON on SQLite."""

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy.types import JSON, TypeDecorator


class EmbeddingVector(TypeDecorator[list[float]]):
    """1536-dim embedding vector."""

    impl = JSON
    cache_ok = True
    dimensions = 1536

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PgVector(self.dimensions))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, _dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value, _dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        return list(value)
