from __future__ import annotations

import re

from app.domain.ner import Entity, NerResponse


PATTERNS: tuple[tuple[str, str], ...] = (
    ("repo_name", r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"),
    ("file_path", r"(?<!\w)(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+\b"),
    ("version_string", r"\bv?\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9_.-]+)?\b"),
    ("error_code", r"\b(?:[A-Z][A-Za-z]+Error|[A-Z]{2,}[-_]\d+|[A-Z]{3,}\d{2,})\b"),
    ("symbol", r"\b[A-Za-z_][A-Za-z0-9_]*\(\)|`[A-Za-z_][A-Za-z0-9_.:]*`|\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b"),
)


class NerService:
    def extract(self, text: str) -> NerResponse:
        entities: list[Entity] = []
        occupied: list[range] = []
        for label, pattern in PATTERNS:
            for match in re.finditer(pattern, text):
                span = range(match.start(), match.end())
                if any(_overlaps(span, prior) for prior in occupied):
                    continue
                entities.append(
                    Entity(
                        text=match.group(0).strip("`"),
                        label=label,
                        start=match.start(),
                        end=match.end(),
                    )
                )
                occupied.append(span)
        entities.sort(key=lambda entity: (entity.start, entity.end))
        return NerResponse(entities=entities)


def _overlaps(left: range, right: range) -> bool:
    return left.start < right.stop and right.start < left.stop
