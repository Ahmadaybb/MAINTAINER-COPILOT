from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IssueLabel = Literal["bug", "feature", "docs", "question"]


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1)


class ClassifyResponse(BaseModel):
    label: IssueLabel
    confidence: float = Field(ge=0.0, le=1.0)
    low_confidence: bool
    model_name: str
    model_version: str
    sha256: str
