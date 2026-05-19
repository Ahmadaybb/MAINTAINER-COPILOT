from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.domain.errors import NotFoundError, ToolFailure
from app.domain.memory import LongTermMemoryRead, MemorySource, MemoryWriteResponse
from app.infra.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingClient
from app.infra.redaction import redact_text

if TYPE_CHECKING:
    from app.repositories.memory import LongTermMemoryRepository


CLARIFY_MEMORY_QUESTION = "What exactly would you like me to remember?"


@dataclass(slots=True)
class MemoryRecallResult:
    memories: list[LongTermMemoryRead]
    conflict_note: str | None = None


class LongTermMemoryService:
    def __init__(
        self,
        embeddings: EmbeddingClient | None = None,
        *,
        sessionmaker: Callable[[], Any] | None = None,
        repository_factory: Callable[[Any], LongTermMemoryRepository] | None = None,
    ) -> None:
        self.embeddings = embeddings or EmbeddingClient()
        self._sessionmaker = sessionmaker
        self._repository_factory = repository_factory

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
        with self._session() as session:
            repo = self._repo(session)
            memory = repo.create(
                owner_id=owner_id,
                content=redacted,
                embedding=embedding,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                source=self._orm_memory_source(source),
                superseded_by=superseded_by,
            )
            session.commit()
            return self._to_domain(memory)

    def write_memory_tool(
        self,
        *,
        owner_id: UUID,
        content: str,
        supersedes_id: UUID | None = None,
    ) -> MemoryWriteResponse:
        return self.write_explicit(owner_id=owner_id, content=content, supersedes_id=supersedes_id)

    def write_explicit(
        self,
        *,
        owner_id: UUID,
        content: str,
        supersedes_id: UUID | None = None,
    ) -> MemoryWriteResponse:
        if _needs_clarification(content):
            return MemoryWriteResponse(
                status="needs_clarification",
                message="I need one more detail before storing this memory.",
                clarifying_question=CLARIFY_MEMORY_QUESTION,
            )

        redacted = redact_text(content)
        embedding = self.embeddings.embed_one(redacted)
        with self._session() as session:
            repo = self._repo(session)
            superseded_memory = None
            if supersedes_id is not None:
                superseded_memory = repo.get_owned_active(memory_id=supersedes_id, owner_id=owner_id)
                if superseded_memory is None:
                    raise NotFoundError("The memory to correct was not found.")
            memory = repo.create(
                owner_id=owner_id,
                content=redacted,
                embedding=embedding,
                embedding_model=DEFAULT_EMBEDDING_MODEL,
                source=self._orm_memory_source(MemorySource.EXPLICIT),
            )
            if superseded_memory is not None:
                repo.mark_superseded(memory=superseded_memory, superseded_by=memory.id)
            session.commit()
            return MemoryWriteResponse(
                status="stored",
                message="Memory stored.",
                memory=self._to_domain(memory),
            )

    def list_active(self, *, owner_id: UUID) -> list[LongTermMemoryRead]:
        with self._session() as session:
            rows = self._repo(session).list_active(owner_id=owner_id)
            return [self._to_domain(row) for row in rows]

    def delete(self, *, owner_id: UUID, memory_id: UUID) -> None:
        with self._session() as session:
            repo = self._repo(session)
            memory = repo.get_owned_active(memory_id=memory_id, owner_id=owner_id)
            if memory is None:
                raise NotFoundError("Memory was not found.")
            repo.soft_delete(memory=memory)
            session.commit()

    def recall(self, *, owner_id: UUID, query: str, limit: int = 5) -> MemoryRecallResult:
        embedding = self.embeddings.embed_one(query)
        with self._session() as session:
            rows = self._repo(session).recall(owner_id=owner_id, embedding=embedding, limit=limit)
            memories = [self._to_domain(row) for row in rows]
        conflict_note = None
        if any(memory.superseded_by for memory in memories):
            conflict_note = "Older remembered facts may have been superseded; prefer the newest active fact."
        return MemoryRecallResult(memories=memories, conflict_note=conflict_note)

    def _session(self):
        if self._sessionmaker is not None:
            return self._sessionmaker()
        from app.repositories.db import get_sessionmaker

        return get_sessionmaker()()

    def _repo(self, session) -> LongTermMemoryRepository:
        if self._repository_factory is not None:
            return self._repository_factory(session)
        from app.repositories.memory import LongTermMemoryRepository

        return LongTermMemoryRepository(session)

    def _to_domain(self, memory) -> LongTermMemoryRead:
        if self._repository_factory is not None:
            return LongTermMemoryRead(
                id=memory.id,
                owner_id=memory.owner_id,
                content=memory.content,
                embedding=list(memory.embedding),
                embedding_model=memory.embedding_model,
                source=getattr(memory.source, "value", memory.source),
                superseded_by=memory.superseded_by,
                created_at=memory.created_at,
                deleted_at=memory.deleted_at,
            )
        from app.repositories.memory import long_term_memory_to_domain

        return long_term_memory_to_domain(memory)

    def _orm_memory_source(self, source: MemorySource):
        if self._repository_factory is not None:
            return source
        try:
            from app.repositories.models.memory import MemorySource as OrmMemorySource

            return OrmMemorySource(source.value)
        except Exception as exc:  # noqa: BLE001 - memory writes must map infra failures to a domain error.
            raise ToolFailure("Memory storage is temporarily unavailable.") from exc


def _needs_clarification(content: str) -> bool:
    normalized = " ".join(content.strip().lower().split())
    ambiguous = {
        "remember",
        "remember this",
        "remember that",
        "please remember",
        "save this",
        "store this",
        "this",
        "that",
    }
    return normalized in ambiguous or len(normalized) < 4
