from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:  # pragma: no cover - production image installs OpenTelemetry.
    trace = None
    JaegerExporter = None
    Resource = None
    ReadableSpan = object
    TracerProvider = None

    class BatchSpanProcessor:  # type: ignore[no-redef]
        def __init__(self, exporter=None) -> None:
            self.exporter = exporter

        def on_end(self, span) -> None:
            return None

from app.infra.redaction import redact


class RedactingSpanProcessor(BatchSpanProcessor):
    def on_end(self, span: ReadableSpan) -> None:
        mutable_attributes = getattr(span, "_attributes", None)
        if mutable_attributes is not None:
            for key, value in list(mutable_attributes.items()):
                mutable_attributes[key] = _redact_attribute(value)
        super().on_end(span)


def _redact_attribute(value: Any) -> Any:
    redacted = redact(value)
    if isinstance(redacted, (str, bool, int, float)) or redacted is None:
        return redacted
    if isinstance(redacted, Sequence) and not isinstance(redacted, (bytes, bytearray, str)):
        return [_redact_attribute(item) for item in redacted]
    if isinstance(redacted, Mapping):
        return str(redacted)
    return redacted


def configure_tracing(service_name: str = "maintainer-copilot-api") -> None:
    if trace is None or TracerProvider is None or Resource is None or JaegerExporter is None:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = JaegerExporter(agent_host_name="jaeger", agent_port=6831)
    provider.add_span_processor(RedactingSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer(name: str):
    if trace is None:
        return _NoopTracer()
    return trace.get_tracer(name)


class _NoopTracer:
    def start_as_current_span(self, _name: str):
        class NoopSpanContext:
            def __enter__(self):
                return _NoopSpan()

            def __exit__(self, exc_type, exc, traceback):
                return None

        return NoopSpanContext()


class _NoopSpan:
    def set_attribute(self, _key: str, _value: Any) -> None:
        return None


@contextmanager
def traced_call(kind: str, name: str, attributes: Mapping[str, Any] | None = None):
    with get_tracer("maintainer-copilot.tools").start_as_current_span(f"{kind}.{name}") as span:
        span.set_attribute("call.kind", kind)
        span.set_attribute("call.name", name)
        for key, value in redact(attributes or {}).items():
            span.set_attribute(str(key), _redact_attribute(value))
        yield span
