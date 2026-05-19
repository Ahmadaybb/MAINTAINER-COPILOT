from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import require_user
from app.domain.memory import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from app.domain.user import AuthenticatedUser

if TYPE_CHECKING:
    from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    from app.services.chat_service import ChatService

    return ChatService()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatSessionResponse:
    return service.create_session(user.id)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    payload: ChatMessageRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatMessageResponse:
    return await service.send_message(
        session_id=session_id,
        user_id=user.id,
        content=payload.content,
        request_id=request.state.request_id,
    )
