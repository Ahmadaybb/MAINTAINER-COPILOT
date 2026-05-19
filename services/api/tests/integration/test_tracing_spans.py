from __future__ import annotations

from app.infra.tracing import _redact_attribute, traced_call


class FakeSpan:
    def __init__(self) -> None:
        self.attributes = {}

    def set_attribute(self, key, value) -> None:
        self.attributes[key] = value


def test_trace_helper_redacts_llm_tool_and_rag_attributes(monkeypatch) -> None:
    spans: list[FakeSpan] = []

    class FakeTracer:
        def start_as_current_span(self, _name):
            class SpanContext:
                def __enter__(self):
                    span = FakeSpan()
                    spans.append(span)
                    return span

                def __exit__(self, exc_type, exc, traceback):
                    return None

            return SpanContext()

    monkeypatch.setattr("app.infra.tracing.get_tracer", lambda _name: FakeTracer())

    for kind, name in (("llm", "complete"), ("tool", "classify_issue"), ("rag", "retrieval")):
        with traced_call(kind, name, {"email": "user@example.com", "token": "secret-token"}):
            pass

    assert [span.attributes["call.kind"] for span in spans] == ["llm", "tool", "rag"]
    for span in spans:
        assert span.attributes["email"] == "[REDACTED]"
        assert span.attributes["token"] == "[REDACTED]"


def test_span_attribute_redaction_handles_nested_values() -> None:
    redacted = _redact_attribute({"authorization": "Bearer abc.def", "prompt": "email user@example.com"})

    assert "abc.def" not in redacted
    assert "user@example.com" not in redacted
