from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

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
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = JaegerExporter(agent_host_name="jaeger", agent_port=6831)
    provider.add_span_processor(RedactingSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer(name: str):
    return trace.get_tracer(name)
