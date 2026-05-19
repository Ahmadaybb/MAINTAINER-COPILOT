from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MemorySource(StrEnum):
    INFERRED = "inferred"
    EXPLICIT = "explicit"


class ConversationSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    widget_config_id: UUID | None = None
    created_at: datetime | None = None
    ended_at: datetime | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    session_id: UUID
    role: MessageRole
    content: str
    tool_calls: list[dict] | None = None
    created_at: datetime | None = None


class LongTermMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    owner_id: UUID
    content: str
    embedding: list[float] | None = None
    embedding_model: str
    source: MemorySource
    superseded_by: UUID | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None


class ExplicitMemoryRequest(BaseModel):
    content: str = Field(min_length=1)
    supersedes_id: UUID | None = None


class MemoryWriteResponse(BaseModel):
    status: str
    message: str
    memory: LongTermMemoryRead | None = None
    clarifying_question: str | None = None


class MemoryDeleteResponse(BaseModel):
    id: UUID
    deleted: bool


class ChatSessionResponse(BaseModel):
    session_id: UUID


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ChatToolCall(BaseModel):
    name: str
    ok: bool
    note: str | None = None


class ChatAssistantMessage(BaseModel):
    role: MessageRole = MessageRole.ASSISTANT
    content: str
    tool_calls: list[ChatToolCall] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    message: ChatAssistantMessage
