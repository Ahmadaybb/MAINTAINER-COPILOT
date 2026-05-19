from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.memory import LongTermMemoryRead, MemorySource
from app.infra.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingClient
from app.infra.redaction import redact_text
from app.repositories.db import get_sessionmaker
from app.repositories.memory import LongTermMemoryRepository, long_term_memory_to_domain
from app.repositories.models.memory import MemorySource as OrmMemorySource


@dataclass(slots=True)
class MemoryRecallResult:
    memories: list[LongTermMemoryRead]
    conflict_note: str | None = None


class LongTermMemoryService:
    def __init__(self, embeddings: EmbeddingClient | None = None) -> None:
        self.embeddings = embeddings or EmbeddingClient()

    def write(
        self,
        *,
        owner_id: UUID,
        content: str,
        source: MemorySource = MemorySource.INFERRED,
        superseded_by: UUID | None = None,
    ) -> LongTermMemoryRead:
        redacted = redact_text(content)
        embedding = self.embeddings.embed_one(redacted)
        with get_sessionmaker()() as session:
            memory = LongTermMemoryRepository(session).create(
                owner_id=owner_id,
                content=redacted,
                embedding=embedding,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                source=OrmMemorySource(source.value),
                superseded_by=superseded_by,
            )
            session.commit()
            return long_term_memory_to_domain(memory)

    def recall(self, *, owner_id: UUID, query: str, limit: int = 5) -> MemoryRecallResult:
        embedding = self.embeddings.embed_one(query)
        with get_sessionmaker()() as session:
            rows = LongTermMemoryRepository(session).recall(owner_id=owner_id, embedding=embedding, limit=limit)
            memories = [long_term_memory_to_domain(row) for row in rows]
        conflict_note = None
        if any(memory.superseded_by for memory in memories):
            conflict_note = "Older remembered facts may have been superseded; prefer the newest active fact."
        return MemoryRecallResult(memories=memories, conflict_note=conflict_note)
