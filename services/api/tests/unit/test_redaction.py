from __future__ import annotations

from app.infra.redaction import REDACTED, redact, redact_text


def test_redacts_secrets_and_pii_from_logs() -> None:
    text = "email maintainer@example.com token=super-secret Bearer abc.def"

    redacted = redact_text(text)

    assert "maintainer@example.com" not in redacted
    assert "super-secret" not in redacted
    assert "abc.def" not in redacted
    assert REDACTED in redacted


def test_redacts_spans_and_nested_payloads() -> None:
    payload = {
        "authorization": "Bearer abc.def",
        "nested": {"email": "user@example.com", "message": "password: hunter2"},
    }

    redacted = redact(payload)

    assert redacted["authorization"] == REDACTED
    assert redacted["nested"]["email"] == REDACTED
    assert "hunter2" not in redacted["nested"]["message"]


def test_memory_write_content_is_redacted_before_persistence() -> None:
    content = redact_text("Remember email user@example.com and api_key=abc123")

    assert "user@example.com" not in content
    assert "abc123" not in content
