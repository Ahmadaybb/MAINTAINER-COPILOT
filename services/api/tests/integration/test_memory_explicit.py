from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.domain.errors import NotFoundError
from app.services.long_term_memory import LongTermMemoryService


class FakeEmbeddings:
    def embed_one(self, text: str) -> list[float]:
        return [float(len(text)), 0.0, 0.0]


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def commit(self) -> None:
        return None


class InMemoryMemoryRepository:
    rows: list[SimpleNamespace] = []

    def __init__(self, _session) -> None:
        return None

    def create(self, **kwargs):
        memory = SimpleNamespace(
            id=uuid4(),
            created_at=datetime.now(UTC),
            deleted_at=None,
            superseded_by=kwargs.get("superseded_by"),
            **{key: value for key, value in kwargs.items() if key != "superseded_by"},
        )
        self.rows.append(memory)
        return memory

    def list_active(self, *, owner_id):
        return [
            row
            for row in self.rows
            if row.owner_id == owner_id and row.deleted_at is None and row.superseded_by is None
        ]

    def get_owned_active(self, *, memory_id, owner_id):
        return next((row for row in self.list_active(owner_id=owner_id) if row.id == memory_id), None)

    def mark_superseded(self, *, memory, superseded_by):
        memory.superseded_by = superseded_by
        return memory

    def soft_delete(self, *, memory):
        memory.deleted_at = datetime.now(UTC)
        return memory

    def recall(self, *, owner_id, embedding, limit=5):
        return self.list_active(owner_id=owner_id)[:limit]


def build_service() -> LongTermMemoryService:
    InMemoryMemoryRepository.rows = []
    return LongTermMemoryService(
        embeddings=FakeEmbeddings(),
        sessionmaker=FakeSession,
        repository_factory=InMemoryMemoryRepository,
    )


def test_explicit_memory_write_confirms_stored_and_is_recalled() -> None:
    service = build_service()
    owner_id = uuid4()

    response = service.write_memory_tool(owner_id=owner_id, content="Preferred package manager is uv")

    assert response.status == "stored"
    assert response.memory is not None
    assert response.memory.source == "explicit"
    recalled = service.recall(owner_id=owner_id, query="package manager")
    assert [memory.content for memory in recalled.memories] == ["Preferred package manager is uv"]


def test_ambiguous_explicit_memory_asks_one_clarifying_question() -> None:
    service = build_service()

    response = service.write_memory_tool(owner_id=uuid4(), content="remember this")

    assert response.status == "needs_clarification"
    assert response.memory is None
    assert response.clarifying_question is not None
    assert response.clarifying_question.count("?") == 1
    assert service.list_active(owner_id=uuid4()) == []


def test_delete_soft_deletes_and_memory_is_never_recalled() -> None:
    service = build_service()
    owner_id = uuid4()
    stored = service.write_memory_tool(owner_id=owner_id, content="Use issue label needs-triage").memory
    assert stored is not None

    service.delete(owner_id=owner_id, memory_id=stored.id)

    assert service.list_active(owner_id=owner_id) == []
    assert service.recall(owner_id=owner_id, query="triage").memories == []


def test_correction_creates_new_memory_and_supersedes_without_in_place_edit() -> None:
    service = build_service()
    owner_id = uuid4()
    old = service.write_memory_tool(owner_id=owner_id, content="Preferred branch is master").memory
    assert old is not None

    new = service.write_memory_tool(
        owner_id=owner_id,
        content="Preferred branch is main",
        supersedes_id=old.id,
    ).memory

    assert new is not None
    active = service.list_active(owner_id=owner_id)
    assert [memory.content for memory in active] == ["Preferred branch is main"]
    assert InMemoryMemoryRepository.rows[0].content == "Preferred branch is master"
    assert InMemoryMemoryRepository.rows[0].superseded_by == new.id
    assert service.recall(owner_id=owner_id, query="branch").memories[0].id == new.id


def test_correction_requires_owned_active_memory() -> None:
    service = build_service()

    try:
        service.write_memory_tool(owner_id=uuid4(), content="Corrected preference", supersedes_id=uuid4())
    except NotFoundError:
        return

    raise AssertionError("Expected missing correction target to raise NotFoundError")
