from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.auth import get_invitation_service
from app.api.deps import require_admin
from app.domain.invitation import InvitationCreate, InvitationRead
from app.domain.user import AuthenticatedUser
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/api/v1/admin", tags=["admin-invitations"])


@router.post(
    "/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationCreate,
    admin: Annotated[AuthenticatedUser, Depends(require_admin)],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> InvitationRead:
    return invitation_service.create_invitation(email=payload.email, invited_by=admin)
