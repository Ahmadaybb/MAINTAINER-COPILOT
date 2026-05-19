from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.domain.errors import NotFoundError
from app.domain.widget import WidgetConfigCreate, WidgetConfigUpdate
from app.services.widget_config_service import EMPTY_ORIGINS_WARNING, WidgetConfigService


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def commit(self) -> None:
        return None


class InMemoryWidgetConfigRepository:
    rows: list[SimpleNamespace] = []

    def __init__(self, _session) -> None:
        return None

    def create(self, **kwargs):
        config = SimpleNamespace(id=uuid4(), created_at=datetime.now(UTC), **kwargs)
        self.rows.append(config)
        return config

    def list(self):
        return list(reversed(self.rows))

    def get(self, widget_id):
        return next((row for row in self.rows if row.id == widget_id), None)

    def update(self, config, **kwargs):
        for field, value in kwargs.items():
            if value is not None:
                setattr(config, field, value)
        return config


def build_service() -> WidgetConfigService:
    InMemoryWidgetConfigRepository.rows = []
    return WidgetConfigService(
        sessionmaker=FakeSession,
        repository_factory=InMemoryWidgetConfigRepository,
    )


def test_create_widget_config_returns_single_script_embed_snippet() -> None:
    service = build_service()
    admin_id = uuid4()

    response = service.create(
        WidgetConfigCreate(
            name="Docs widget",
            theme={"accent": "#2563eb"},
            allowed_origins=["https://docs.example.com"],
            greeting="Ask about this project",
            enabled_tools=["triage", "rag_search"],
            host_token_verify_key="verify-key",
        ),
        created_by=admin_id,
    )

    assert response.created_by == admin_id
    assert response.allowed_origins == ["https://docs.example.com"]
    assert response.warnings == []
    assert response.embed_snippet == f'<script src="/widget.js" data-widget-id="{response.id}" async></script>'
    assert response.embed_snippet.count("<script") == 1
    assert "data-widget-id=" in response.embed_snippet


def test_edit_widget_config_reflects_updated_greeting_and_tools() -> None:
    service = build_service()
    created = service.create(
        WidgetConfigCreate(
            name="Maintainer widget",
            allowed_origins=["https://host.example.com"],
            greeting="Hello",
            enabled_tools=["triage"],
            host_token_verify_key="verify-key",
        ),
        created_by=uuid4(),
    )

    updated = service.update(
        created.id,
        WidgetConfigUpdate(greeting="What should we triage?", enabled_tools=["triage", "write_memory"]),
    )

    assert updated.id == created.id
    assert updated.greeting == "What should we triage?"
    assert updated.enabled_tools == ["triage", "write_memory"]
    assert updated.embed_snippet == created.embed_snippet
    assert service.list()[0].greeting == "What should we triage?"
    assert service.get(created.id).enabled_tools == ["triage", "write_memory"]


def test_empty_allowed_origins_returns_warning() -> None:
    service = build_service()

    response = service.create(
        WidgetConfigCreate(
            name="Unpublished widget",
            allowed_origins=[],
            greeting="Hello",
            enabled_tools=["triage"],
            host_token_verify_key="verify-key",
        ),
        created_by=uuid4(),
    )

    assert response.allowed_origins == []
    assert response.warnings == [EMPTY_ORIGINS_WARNING]


def test_update_missing_widget_maps_to_domain_not_found() -> None:
    service = build_service()

    try:
        service.update(uuid4(), WidgetConfigUpdate(greeting="Nope"))
    except NotFoundError:
        return

    raise AssertionError("Expected missing widget config to raise NotFoundError")
