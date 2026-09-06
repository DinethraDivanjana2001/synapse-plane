"""Dialect-aware embedding column type.

Production runs on PostgreSQL + pgvector (real cosine-distance search).
Local dev/tests run on SQLite, which has no vector extension, so this type
falls back to a JSON-encoded float list there. Cosine similarity search
(HybridContextRetriever, Step 2b) only needs to work against the pgvector
path — the SQLite path exists purely so Step 1/2 can be built and tested on
a machine without Docker/Postgres. See docs/DECISIONS.md ADR-009.
"""

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy.types import JSON, TypeDecorator


class EmbeddingVector(TypeDecorator[list[float]]):
    """1536-dim embedding vector; real `vector` type on Postgres, JSON on SQLite.

    process_bind_param/process_result_value only normalize to/from a plain
    list[float] — the resolved per-dialect impl (PgVector or JSON, chosen in
    load_dialect_impl) does its own serialization. Pre-serializing here too
    would double-encode under JSON (str gets JSON-quoted a second time).
    """

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
