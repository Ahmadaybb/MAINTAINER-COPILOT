from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_WIDGET_THEME = {
    "color": "#0f172a",
    "background": "#ffffff",
    "accent": "#2563eb",
    "fontFamily": "Inter, system-ui, sans-serif",
}


class WidgetConfigBase(BaseModel):
    name: str = Field(min_length=1)
    theme: dict = Field(default_factory=lambda: dict(DEFAULT_WIDGET_THEME))
    allowed_origins: list[str] = Field(default_factory=list)
    greeting: str = Field(default="How can I help triage this project?")
    enabled_tools: list[str] = Field(default_factory=lambda: ["triage", "rag_search", "write_memory"])
    host_token_verify_key: str = Field(min_length=1)


class WidgetConfigCreate(WidgetConfigBase):
    pass


class WidgetConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    theme: dict | None = None
    allowed_origins: list[str] | None = None
    greeting: str | None = None
    enabled_tools: list[str] | None = None
    host_token_verify_key: str | None = Field(default=None, min_length=1)


class WidgetConfigRead(WidgetConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by: UUID
    created_at: datetime | None = None
    embed_snippet: str
    warnings: list[str] = Field(default_factory=list)


class PublicWidgetConfig(BaseModel):
    theme: dict
    greeting: str
    enabled_tools: list[str]


class WidgetSessionRequest(BaseModel):
    widget_id: UUID
    host_token: str | None = None


class WidgetSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
