from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|authorization|jwt)", re.IGNORECASE)
BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+\b")
GENERIC_SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^'\"\s,;]+")


def redact_text(value: str) -> str:
    redacted = EMAIL_RE.sub(REDACTED, value)
    redacted = BEARER_RE.sub(f"Bearer {REDACTED}", redacted)
    return GENERIC_SECRET_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", redacted)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {key: REDACTED if SECRET_KEY_RE.search(str(key)) else redact(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
