from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.widget import WidgetConfigRead
from app.services.widget_config_service import public_widget_config, widget_origin_policy_headers


def widget_config(*, allowed_origins: list[str]) -> WidgetConfigRead:
    return WidgetConfigRead(
        id=uuid4(),
        name="Docs widget",
        theme={"accent": "#2563eb"},
        allowed_origins=allowed_origins,
        greeting="Ask about this project",
        enabled_tools=["triage", "rag_search"],
        host_token_verify_key="verify-key",
        created_by=uuid4(),
        created_at=datetime.now(UTC),
        embed_snippet='<script src="/widget.js" data-widget-id="widget-id" async></script>',
    )


def test_allowlisted_origin_receives_csp_and_scoped_cors() -> None:
    headers = widget_origin_policy_headers(
        allowed_origins=["https://docs.example.com", "https://app.example.com"],
        request_origin="https://docs.example.com",
    )

    assert headers["Content-Security-Policy"] == (
        "frame-ancestors https://docs.example.com https://app.example.com"
    )
    assert headers["Access-Control-Allow-Origin"] == "https://docs.example.com"
    assert headers["Vary"] == "Origin"


def test_non_allowlisted_origin_gets_no_cors_and_is_blocked_by_csp() -> None:
    headers = widget_origin_policy_headers(
        allowed_origins=["https://docs.example.com"],
        request_origin="https://evil.example.com",
    )

    assert headers["Content-Security-Policy"] == "frame-ancestors https://docs.example.com"
    assert "Access-Control-Allow-Origin" not in headers


def test_empty_allowed_origins_uses_none_frame_ancestors() -> None:
    headers = widget_origin_policy_headers(allowed_origins=[], request_origin="https://docs.example.com")

    assert headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert "Access-Control-Allow-Origin" not in headers


def test_removed_origin_is_blocked_on_new_loads() -> None:
    updated = widget_config(allowed_origins=["https://new.example.com"])

    headers = widget_origin_policy_headers(
        allowed_origins=updated.allowed_origins,
        request_origin="https://old.example.com",
    )

    assert headers["Content-Security-Policy"] == "frame-ancestors https://new.example.com"
    assert "Access-Control-Allow-Origin" not in headers


def test_public_widget_config_excludes_admin_only_fields() -> None:
    public_config = public_widget_config(widget_config(allowed_origins=["https://docs.example.com"]))
    payload = public_config.model_dump()

    assert payload == {
        "theme": {"accent": "#2563eb"},
        "greeting": "Ask about this project",
        "enabled_tools": ["triage", "rag_search"],
    }
    assert "host_token_verify_key" not in payload
    assert "allowed_origins" not in payload
