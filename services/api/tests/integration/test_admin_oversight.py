from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services.long_term_memory import LongTermMemoryService


REPO_ROOT = Path(__file__).resolve().parents[4]


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class InMemoryMemoryRepository:
    rows: list[SimpleNamespace] = []

    def __init__(self, _session) -> None:
        return None

    def list_active(self, *, owner_id):
        return [
            row
            for row in self.rows
            if row.owner_id == owner_id and row.deleted_at is None and row.superseded_by is None
        ]


def test_admin_can_inspect_another_owners_active_memory_entries() -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    InMemoryMemoryRepository.rows = [
        memory(owner_id=owner_id, content="Preferred release day is Tuesday"),
        memory(owner_id=other_owner_id, content="Other user memory"),
        memory(owner_id=owner_id, content="Deleted memory", deleted=True),
        memory(owner_id=owner_id, content="Superseded memory", superseded_by=uuid4()),
    ]
    service = LongTermMemoryService(
        embeddings=SimpleNamespace(embed_one=lambda _text: [1.0, 0.0, 0.0]),
        sessionmaker=FakeSession,
        repository_factory=InMemoryMemoryRepository,
    )

    result = service.list_active(owner_id=owner_id)

    assert len(result) == 1
    assert result[0].owner_id == owner_id
    assert result[0].content == "Preferred release day is Tuesday"


def test_admin_memory_router_is_admin_only() -> None:
    source = (REPO_ROOT / "services" / "api" / "app" / "api" / "admin_memory.py").read_text(encoding="utf-8")

    assert 'prefix="/api/v1/admin/memory"' in source
    assert "Depends(require_admin)" in source
    assert "require_user" not in source


def test_streamlit_admin_ui_calls_api_over_http_only() -> None:
    chatbot_root = REPO_ROOT / "services" / "chatbot"
    sources = "\n".join(path.read_text(encoding="utf-8") for path in chatbot_root.rglob("*.py"))

    assert "httpx.Client" in sources
    assert "/admin/widgets" in sources
    assert "/admin/memory" in sources
    assert "/chat/sessions" in sources
    forbidden = ("sqlalchemy", "redis", "vault", "app.repositories", "psycopg", "pgvector")
    assert not any(term in sources.lower() for term in forbidden)


def test_streamlit_has_requested_admin_and_chat_pages() -> None:
    pages = {path.name for path in (REPO_ROOT / "services" / "chatbot" / "pages").glob("*.py")}

    assert "1_Widget_Config.py" in pages
    assert "2_Memory_Inspector.py" in pages
    assert "3_Chat.py" in pages


def memory(*, owner_id, content: str, deleted: bool = False, superseded_by=None):
    return SimpleNamespace(
        id=uuid4(),
        owner_id=owner_id,
        content=content,
        embedding=[1.0, 0.0, 0.0],
        embedding_model="test-embedding",
        source="explicit",
        superseded_by=superseded_by,
        created_at=datetime.now(UTC),
        deleted_at=datetime.now(UTC) if deleted else None,
    )
