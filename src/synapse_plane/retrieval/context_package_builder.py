"""Assembles the final, token-bounded ContextPackage from scored candidates."""

from datetime import UTC, datetime

from synapse_plane.domain.memory import ContextItem, ContextPackage

_WORDS_TO_TOKENS = 1.3


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

        # exclude expired (treat naive datetimes as UTC)
        live_items = [
            item
            for item in scored_items
            if item.memory.valid_to is None
            or (item.memory.valid_to.replace(tzinfo=item.memory.valid_to.tzinfo or UTC) > now)
        ]

        # dedupe by memory_id, keep highest score
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
