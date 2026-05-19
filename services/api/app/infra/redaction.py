from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|authorization|jwt|otel[_-]?exporter[_-]?key)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+\b")
GITHUB_TOKEN_RE = re.compile(r"\b(ghp|github_pat|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")
GENERIC_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^'\"\s,;]+"
)


def redact_text(value: str) -> str:
    redacted = EMAIL_RE.sub(REDACTED, value)
    redacted = BEARER_RE.sub(f"Bearer {REDACTED}", redacted)
    redacted = GITHUB_TOKEN_RE.sub(REDACTED, redacted)
    return GENERIC_SECRET_RE.sub(_redact_secret_assignment, redacted)


def _redact_secret_assignment(match: re.Match[str]) -> str:
    prefix = match.group(0).split(match.group(1), maxsplit=1)[0]
    return f"{prefix}{match.group(1)}={REDACTED}"


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            key: REDACTED if SECRET_KEY_RE.search(str(key)) else redact(nested)
            for key, nested in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item) for item in value]
    return value


def redact_json(value: Mapping[str, Any]) -> str:
    return json.dumps(redact(value), sort_keys=True, default=str)
