from __future__ import annotations

from app.infra.redaction import REDACTED, redact, redact_text


def test_modelserver_redacts_secret_and_pii_text() -> None:
    redacted = redact_text("classifier token=secret maintainer@example.com Bearer abc.def")

    assert "secret" not in redacted
    assert "maintainer@example.com" not in redacted
    assert "abc.def" not in redacted
    assert REDACTED in redacted


def test_modelserver_redacts_nested_span_like_attributes() -> None:
    redacted = redact({"api_key": "abc", "payload": ["user@example.com"]})

    assert redacted["api_key"] == REDACTED
    assert redacted["payload"] == [REDACTED]
