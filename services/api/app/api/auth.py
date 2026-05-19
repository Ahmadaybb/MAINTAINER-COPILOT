from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.domain.errors import PermissionDenied
from app.domain.invitation import AcceptInviteRequest, TokenResponse
from app.infra.logging import current_trace_id
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def get_auth_service() -> AuthService:
    return AuthService()


def get_invitation_service() -> InvitationService:
    return InvitationService()


@router.post("/jwt/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse | JSONResponse:
    try:
        return auth_service.login(str(payload.email), payload.password)
    except PermissionDenied:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "permission_denied",
                    "message": "Invalid email or password.",
                    "request_id": request.state.request_id,
                    "trace_id": current_trace_id(),
                }
            },
        )


@router.post("/jwt/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    payload: AcceptInviteRequest,
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> TokenResponse:
    return invitation_service.accept_invite(token=payload.token, password=payload.password)
