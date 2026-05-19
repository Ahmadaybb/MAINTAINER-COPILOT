from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.domain.errors import UnauthorizedError
from app.domain.widget import WidgetSessionRequest
from app.services.widget_config_service import WidgetConfigService, sign_host_token


VERIFY_KEY = "host-shared-verification-key"
REPO_ROOT = Path(__file__).resolve().parents[4]


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def commit(self) -> None:
        return None


class InMemoryWidgetConfigRepository:
    widget_id = uuid4()
    rows = [
        SimpleNamespace(
            id=widget_id,
            name="Demo widget",
            theme={"accent": "#2563eb"},
            allowed_origins=["http://localhost:8080"],
            greeting="Ask about this project",
            enabled_tools=["triage", "rag_search"],
            host_token_verify_key=VERIFY_KEY,
            created_by=uuid4(),
            created_at=datetime.now(UTC),
        )
    ]

    def __init__(self, _session) -> None:
        return None

    def get(self, widget_id):
        return next((row for row in self.rows if row.id == widget_id), None)

    def list(self):
        return self.rows


def build_service() -> WidgetConfigService:
    return WidgetConfigService(
        sessionmaker=FakeSession,
        repository_factory=InMemoryWidgetConfigRepository,
        token_minter=lambda user: f"scoped-token:{user.id}:{user.email}",
    )


def valid_host_token(*, widget_id=None, subject=None, expires_delta=timedelta(minutes=5), key=VERIFY_KEY) -> str:
    subject = subject or uuid4()
    widget_id = widget_id or InMemoryWidgetConfigRepository.widget_id
    return sign_host_token(
        payload={
            "sub": str(subject),
            "email": "maintainer@example.com",
            "widget_id": str(widget_id),
            "exp": int((datetime.now(UTC) + expires_delta).timestamp()),
        },
        verify_key=key,
    )


def test_valid_host_token_returns_scoped_access_token() -> None:
    service = build_service()
    subject = uuid4()

    response = service.create_widget_session(
        WidgetSessionRequest(
            widget_id=InMemoryWidgetConfigRepository.widget_id,
            host_token=valid_host_token(subject=subject),
        )
    )

    assert response.token_type == "bearer"
    assert response.access_token == f"scoped-token:{subject}:maintainer@example.com"


def test_missing_host_token_is_denied_generically_without_login_ui() -> None:
    service = build_service()

    try:
        service.create_widget_session(WidgetSessionRequest(widget_id=InMemoryWidgetConfigRepository.widget_id))
    except UnauthorizedError as exc:
        assert exc.message == "Widget authentication failed."
        assert "login" not in exc.message.lower()
        return

    raise AssertionError("Expected missing host token to be denied")


def test_invalid_host_token_is_denied_generically() -> None:
    service = build_service()

    try:
        service.create_widget_session(
            WidgetSessionRequest(widget_id=InMemoryWidgetConfigRepository.widget_id, host_token="not-a-token")
        )
    except UnauthorizedError as exc:
        assert exc.message == "Widget authentication failed."
        assert "signature" not in exc.message.lower()
        return

    raise AssertionError("Expected invalid host token to be denied")


def test_expired_host_token_is_denied_generically() -> None:
    service = build_service()

    try:
        service.create_widget_session(
            WidgetSessionRequest(
                widget_id=InMemoryWidgetConfigRepository.widget_id,
                host_token=valid_host_token(expires_delta=timedelta(minutes=-1)),
            )
        )
    except UnauthorizedError as exc:
        assert exc.message == "Widget authentication failed."
        assert "expired" not in exc.message.lower()
        return

    raise AssertionError("Expected expired host token to be denied")


def test_wrong_widget_token_is_denied() -> None:
    service = build_service()

    try:
        service.create_widget_session(
            WidgetSessionRequest(
                widget_id=InMemoryWidgetConfigRepository.widget_id,
                host_token=valid_host_token(widget_id=uuid4()),
            )
        )
    except UnauthorizedError:
        return

    raise AssertionError("Expected widget-id mismatch to be denied")


def test_demo_host_uses_one_script_tag_for_configured_widget_id() -> None:
    host_html = (REPO_ROOT / "services" / "host" / "index.html").read_text(encoding="utf-8")
    demo_config = (REPO_ROOT / "services" / "host" / "widget-config.example.json").read_text(encoding="utf-8")

    assert host_html.count("<script") == 1
    assert 'src="http://localhost:8000/widget.js"' in host_html
    assert 'data-widget-id="00000000-0000-4000-8000-000000000001"' in host_html
    assert '"id": "00000000-0000-4000-8000-000000000001"' in demo_config
    assert '"http://localhost:8080"' in demo_config


def test_widget_source_has_no_copilot_login_ui_and_uses_enabled_tools() -> None:
    widget_source = (REPO_ROOT / "services" / "widget" / "src" / "main.jsx").read_text(encoding="utf-8")

    assert "enabled_tools" in widget_source
    assert 'type: "copilot:resize"' in widget_source
    assert "login" not in widget_source.lower()
