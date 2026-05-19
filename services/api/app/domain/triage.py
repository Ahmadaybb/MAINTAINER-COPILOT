from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


IssueLabel = Literal["bug", "feature", "docs", "question"]
EntityLabel = Literal["repo_name", "error_code", "version_string", "symbol", "file_path"]


class TriageRequest(BaseModel):
    issue_url: HttpUrl | None = None
    issue_text: str | None = Field(default=None, min_length=1)


class Classification(BaseModel):
    label: IssueLabel
    confidence: float = Field(ge=0.0, le=1.0)
    low_confidence: bool
    model_name: str | None = None
    model_version: str | None = None
    sha256: str | None = None


class Entity(BaseModel):
    text: str
    label: EntityLabel
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class TriageResponse(BaseModel):
    classification: Classification | None = None
    entities: list[Entity] = Field(default_factory=list)
    summary: str | None = None
    request_id: str
    notes: list[str] = Field(default_factory=list)
