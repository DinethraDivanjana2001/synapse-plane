"""Memory ingestion pipeline: save raw content first, then derive structure.

LLM extraction output is always a proposal, never authoritative — the raw
Memory.content is preserved regardless of extraction quality (see
docs/MEMORY_AND_RAG.md "important rule").
"""

import re
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from synapse_plane.domain.enums import ExplicitOrInferred, MemoryType
from synapse_plane.domain.memory import ExtractedEntity, Memory, MemoryExtractionResult
from synapse_plane.memory.embedding_service import EmbeddingServiceProtocol
from synapse_plane.persistence.repositories import EntityRepository, MemoryRepository

_EXTRACTION_PROMPT = """Extract structured information from this personal note.
Return JSON matching this schema:
{{
  "memory_type": "explicit_profile|episodic|preference|goal|relationship|decision|outcome",
  "confidence": 0.0-1.0,
  "explicit_or_inferred": "explicit|inferred",
  "entities": [{{"name": "...", "entity_type": "person|place|restaurant|...",
                 "role": "subject|object"}}],
  "relationships": [{{"source": "...", "relationship_type": "PREFERS|AVOIDS|KNOWS|...",
                      "target": "..."}}]
}}

Note: {content}"""


class MemoryExtractorProtocol(Protocol):
    async def extract(self, content: str) -> MemoryExtractionResult: ...


class LLMMemoryExtractor:
    """Real extractor — OpenAI JSON mode. Never exercised in tests
    (NFR-006); FakeMemoryExtractor is used everywhere instead."""

    def __init__(self, llm_client: object, model: str):
        self.llm_client = llm_client
        self.model = model

    async def extract(self, content: str) -> MemoryExtractionResult:
        response = await self.llm_client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.model,
            messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(content=content)}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return MemoryExtractionResult.model_validate_json(response.choices[0].message.content)


_CAPITALIZED_WORD = re.compile(r"\b[A-Z][a-z]+\b")
_STOPWORDS = {"I", "The", "A", "An", "My", "Her", "His", "She", "He", "They"}


class FakeMemoryExtractor:
    """Deterministic, keyword/regex-based extraction — no network calls.
    Used in all tests and the demo. Deliberately simple: real entity/intent
    understanding belongs to the Context Intelligence Agent (Step 4), not
    this pipeline's test double."""

    async def extract(self, content: str) -> MemoryExtractionResult:
        lowered = content.lower()
        if any(k in lowered for k in ("prefer", " like ", "avoid", "dislike")):
            memory_type = MemoryType.PREFERENCE
        elif any(k in lowered for k in ("trying to", "goal", "aiming", "want to", "saving up")):
            memory_type = MemoryType.GOAL
        elif any(k in lowered for k in ("chose", "decided", "picked")):
            memory_type = MemoryType.DECISION
        elif " is my " in lowered or " is a " in lowered:
            memory_type = MemoryType.RELATIONSHIP
        else:
            memory_type = MemoryType.EPISODIC

        entities = [
            ExtractedEntity(name=word, entity_type="person", role="subject")
            for word in dict.fromkeys(_CAPITALIZED_WORD.findall(content))
            if word not in _STOPWORDS
        ]
        return MemoryExtractionResult(
            memory_type=memory_type,
            confidence=0.85,
            explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
            entities=entities,
            relationships=[],
        )


class MemoryIngestionPipeline:
    def __init__(
        self,
        extractor: MemoryExtractorProtocol,
        embedding_service: EmbeddingServiceProtocol,
        memory_repo: MemoryRepository,
        entity_repo: EntityRepository,
    ):
        self.extractor = extractor
        self.embedding_service = embedding_service
        self.memory_repo = memory_repo
        self.entity_repo = entity_repo

    async def ingest(self, user_id: str, raw_content: str, source: str) -> Memory:
        now = datetime.now(UTC)

        # 1. Save the raw memory BEFORE any LLM processing — the original is
        # never lost even if extraction fails or produces garbage.
        memory = Memory(
            memory_id=str(uuid4()),
            user_id=user_id,
            memory_type=MemoryType.EPISODIC,
            content=raw_content,
            confidence=1.0,
            explicit_or_inferred=ExplicitOrInferred.EXPLICIT,
            valid_from=now,
            source=source,
            created_at=now,
            observed_at=now,
        )
        await self.memory_repo.create(memory)

        # 2-3. Extract structure, update the stored memory with it.
        extraction = await self.extractor.extract(raw_content)
        await self.memory_repo.update_type_and_confidence(
            memory.memory_id, extraction.memory_type, extraction.confidence
        )

        # 4. Entity resolution and linking.
        for entity in extraction.entities:
            canonical_name = entity.name.strip().lower().replace(" ", "_")
            resolved = await self.entity_repo.get_or_create(
                user_id=user_id,
                entity_type=entity.entity_type,
                name=entity.name,
                canonical_name=canonical_name,
            )
            await self.entity_repo.link_to_memory(
                resolved.entity_id, memory.memory_id, role=entity.role
            )

        # 5. Embed and store.
        embedding = await self.embedding_service.embed(raw_content)
        await self.memory_repo.store_embedding(
            memory.memory_id, embedding, self.embedding_service.model
        )

        return memory.model_copy(
            update={
                "memory_type": extraction.memory_type,
                "confidence": extraction.confidence,
                "explicit_or_inferred": extraction.explicit_or_inferred,
            }
        )
