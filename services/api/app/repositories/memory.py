from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.memory import LongTermMemoryRead, MessageRead
from app.repositories.models.memory import (
    ConversationSession,
    LongTermMemory,
    MemorySource,
    Message,
    MessageRole,
)


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, *, user_id: UUID, widget_config_id: UUID | None = None) -> ConversationSession:
        conversation = ConversationSession(user_id=user_id, widget_config_id=widget_config_id)
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_session(self, session_id: UUID) -> ConversationSession | None:
        return self.session.get(ConversationSession, session_id)

    def add_message(
        self,
        *,
        session_id: UUID,
        role: MessageRole,
        content: str,
        tool_calls: list[dict] | None = None,
    ) -> Message:
        message = Message(session_id=session_id, role=role, content=content, tool_calls=tool_calls)
        self.session.add(message)
        self.session.flush()
        return message


class LongTermMemoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        owner_id: UUID,
        content: str,
        embedding: list[float],
        embedding_model: str,
        source: MemorySource,
        superseded_by: UUID | None = None,
    ) -> LongTermMemory:
        memory = LongTermMemory(
            owner_id=owner_id,
            content=content,
            embedding=embedding,
            embedding_model=embedding_model,
            source=source,
            superseded_by=superseded_by,
        )
        self.session.add(memory)
        self.session.flush()
        return memory

    def recall(self, *, owner_id: UUID, embedding: list[float], limit: int = 5) -> list[LongTermMemory]:
        statement = (
            select(LongTermMemory)
            .where(LongTermMemory.owner_id == owner_id)
            .where(LongTermMemory.deleted_at.is_(None))
            .order_by(
                LongTermMemory.embedding.cosine_distance(embedding),
                LongTermMemory.superseded_by.is_not(None),
                LongTermMemory.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.session.execute(statement).scalars())


def message_to_domain(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        session_id=message.session_id,
        role=message.role.value,
        content=message.content,
        tool_calls=message.tool_calls,
        created_at=message.created_at,
    )


def long_term_memory_to_domain(memory: LongTermMemory) -> LongTermMemoryRead:
    return LongTermMemoryRead(
        id=memory.id,
        owner_id=memory.owner_id,
        content=memory.content,
        embedding=list(memory.embedding),
        embedding_model=memory.embedding_model,
        source=memory.source.value,
        superseded_by=memory.superseded_by,
        created_at=memory.created_at,
        deleted_at=memory.deleted_at,
    )
