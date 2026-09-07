"""Unit tests for scoring and package-building — pure functions, no DB."""

from datetime import UTC, datetime, timedelta

from synapse_plane.domain.enums import ExplicitOrInferred, MemoryType
from synapse_plane.domain.memory import ContextItem, Memory
from synapse_plane.retrieval.context_package_builder import ContextPackageBuilder
from synapse_plane.retrieval.context_retriever import score_memory


def _now() -> datetime:
    return datetime.now(UTC)


def make_memory(**overrides: object) -> Memory:
    defaults: dict[str, object] = {
        "memory_id": "mem-1",
        "user_id": "user-1",
        "memory_type": MemoryType.PREFERENCE,
        "content": "I prefer quiet restaurants over lively ones",
        "confidence": 0.9,
        "explicit_or_inferred": ExplicitOrInferred.EXPLICIT,
        "valid_from": _now() - timedelta(days=10),
        "valid_to": None,
        "source": "user_input",
        "created_at": _now() - timedelta(days=10),
        "observed_at": _now() - timedelta(days=10),
    }
    defaults.update(overrides)
    return Memory(**defaults)  # type: ignore[arg-type]


def test_retriever_scores_explicit_higher_than_inferred() -> None:
    explicit = make_memory(explicit_or_inferred=ExplicitOrInferred.EXPLICIT)
    inferred = make_memory(memory_id="mem-2", explicit_or_inferred=ExplicitOrInferred.INFERRED)

    assert score_memory(explicit) > score_memory(inferred)


def test_retriever_includes_entity_matched_memories() -> None:
    memory = make_memory()

    assert score_memory(memory, entity_match=True) > score_memory(memory, entity_match=False)


def test_scoring_formula_produces_expected_range() -> None:
    best = make_memory(confidence=1.0, observed_at=_now())
    score = score_memory(best, semantic_similarity=1.0, entity_match=True)

    # Weights sum to 1.0; a maximal candidate should land close to the top.
    assert 0.0 < score <= 1.0

    worst = make_memory(
        confidence=0.0,
        observed_at=_now() - timedelta(days=1000),
        explicit_or_inferred=ExplicitOrInferred.INFERRED,
        valid_to=_now() - timedelta(days=1),
    )
    assert score_memory(worst, semantic_similarity=0.0, entity_match=False) < 0.0


def test_retriever_excludes_expired_memories() -> None:
    live = make_memory(memory_id="mem-live")
    expired = make_memory(memory_id="mem-expired", valid_to=_now() - timedelta(days=1))

    items = [
        ContextItem(memory=live, relevance_score=0.5, retrieval_reason="semantic_similarity"),
        ContextItem(memory=expired, relevance_score=0.9, retrieval_reason="semantic_similarity"),
    ]
    package = ContextPackageBuilder().build(
        items, intent="find dinner", total_memories_scanned=2, token_budget=2000, max_items=10
    )

    assert [item.memory.memory_id for item in package.items] == ["mem-live"]


def test_retriever_respects_token_budget() -> None:
    long_content = " ".join(["word"] * 100)
    items = [
        ContextItem(
            memory=make_memory(memory_id=f"mem-{i}", content=long_content),
            relevance_score=1.0 - i * 0.01,
            retrieval_reason="semantic_similarity",
        )
        for i in range(10)
    ]

    package = ContextPackageBuilder().build(
        items, intent="find dinner", total_memories_scanned=10, token_budget=150, max_items=10
    )

    assert len(package.items) < 10
    assert package.token_estimate <= 150
