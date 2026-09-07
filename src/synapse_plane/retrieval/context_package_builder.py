"""Assembles the final, token-bounded ContextPackage from scored candidates.

Kept separate from HybridContextRetriever (which does DB access and scoring)
so the trimming/dedup logic is pure and unit-testable without a database —
see tests/unit/test_context_retriever.py.
"""

from datetime import UTC, datetime

from synapse_plane.domain.memory import ContextItem, ContextPackage

_WORDS_TO_TOKENS = 1.3  # rough estimate, matches docs/guide/step_02b


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * _WORDS_TO_TOKENS)


class ContextPackageBuilder:
    def build(
        self,
        scored_items: list[ContextItem],
        intent: str,
        total_memories_scanned: int,
        token_budget: int,
        max_items: int,
    ) -> ContextPackage:
        now = datetime.now(UTC)

        # Defensive expiry filter — most candidates are already filtered at
        # the query level (valid_to IS NULL), but the entity-graph expansion
        # path doesn't guarantee it, so enforce it here too. SQLite (tests)
        # doesn't preserve tzinfo on read even for DateTime(timezone=True);
        # everything this app writes is UTC, so treat naive as UTC.
        live_items = [
            item
            for item in scored_items
            if item.memory.valid_to is None
            or (item.memory.valid_to.replace(tzinfo=item.memory.valid_to.tzinfo or UTC) > now)
        ]

        # Deduplicate by memory_id, keeping the highest-scoring occurrence
        # (a memory can be a candidate via both semantic search and the
        # entity graph).
        best_by_memory: dict[str, ContextItem] = {}
        for item in live_items:
            existing = best_by_memory.get(item.memory.memory_id)
            if existing is None or item.relevance_score > existing.relevance_score:
                best_by_memory[item.memory.memory_id] = item

        ranked = sorted(best_by_memory.values(), key=lambda i: i.relevance_score, reverse=True)

        selected: list[ContextItem] = []
        tokens_used = 0
        for item in ranked:
            if len(selected) >= max_items:
                break
            item_tokens = estimate_tokens(item.memory.content)
            if selected and tokens_used + item_tokens > token_budget:
                continue
            selected.append(item)
            tokens_used += item_tokens

        return ContextPackage(
            items=selected,
            intent=intent,
            retrieved_at=now,
            total_memories_scanned=total_memories_scanned,
            token_estimate=tokens_used,
        )
