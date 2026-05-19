from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from opentelemetry import trace

from app.infra.redaction import redact_json, redact_text

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def current_request_id() -> str:
    return request_id_var.get()


def current_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "-"
    return format(span_context.trace_id, "032x")


class RedactingJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "request_id": getattr(record, "request_id", current_request_id()),
            "trace_id": getattr(record, "trace_id", current_trace_id()),
        }
        if record.exc_info:
            payload["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return redact_json(payload)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        record.trace_id = current_trace_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingJsonFormatter())
    handler.addFilter(RequestContextFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
