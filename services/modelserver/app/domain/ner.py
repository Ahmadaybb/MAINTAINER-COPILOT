from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

EntityLabel = Literal["repo_name", "error_code", "version_string", "symbol", "file_path"]


class NerRequest(BaseModel):
    text: str = Field(min_length=1)


class Entity(BaseModel):
    text: str
    label: EntityLabel
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "Entity":
        if self.end < self.start:
            raise ValueError("end must not precede start")
        return self


class NerResponse(BaseModel):
    entities: list[Entity]
