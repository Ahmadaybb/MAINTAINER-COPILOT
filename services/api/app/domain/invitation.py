from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class InvitationCreate(BaseModel):
    email: EmailStr


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    expires_at: datetime
    invite_token: str | None = None


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
