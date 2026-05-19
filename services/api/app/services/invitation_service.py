from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pydantic import EmailStr

from app.domain.errors import GoneError, NotFoundError
from app.domain.invitation import InvitationRead, TokenResponse
from app.domain.user import AuthenticatedUser, UserRole
from app.infra.auth import create_access_token, hash_password
from app.repositories.db import get_sessionmaker
from app.repositories.invitations import InvitationRepository
from app.repositories.models.user import UserRole as OrmUserRole
from app.repositories.users import UserRepository


class InvitationService:
    def create_invitation(
        self,
        *,
        email: EmailStr,
        invited_by: AuthenticatedUser,
        lifetime_hours: int = 72,
    ) -> InvitationRead:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_invite_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=lifetime_hours)

        with get_sessionmaker()() as session:
            invitation = InvitationRepository(session).create(
                email=str(email),
                token_hash=token_hash,
                invited_by=invited_by.id,
                expires_at=expires_at,
            )
            session.commit()
            return InvitationRead(
                id=invitation.id,
                email=invitation.email,
                expires_at=invitation.expires_at,
                invite_token=raw_token,
            )

    def accept_invite(self, *, token: str, password: str) -> TokenResponse:
        token_hash = hash_invite_token(token)
        now = datetime.now(UTC)
        with get_sessionmaker()() as session:
            invitations = InvitationRepository(session)
            users = UserRepository(session)
            invitation = invitations.get_by_token_hash(token_hash)
            if not invitation:
                raise NotFoundError("Invitation was not found.")
            if invitation.accepted_at is not None or invitation.expires_at <= now:
                raise GoneError("Invitation is expired or already accepted.")

            user = users.get_by_email(invitation.email)
            hashed_password = hash_password(password)
            if user:
                user = users.set_password(user, hashed_password)
            else:
                user = users.create(
                    email=invitation.email,
                    hashed_password=hashed_password,
                    role=OrmUserRole.USER,
                    is_active=True,
                )
            invitations.mark_accepted(invitation, now)
            session.commit()

            domain_user = AuthenticatedUser(
                id=user.id,
                email=user.email,
                role=UserRole(user.role.value),
                is_active=user.is_active,
            )
            return TokenResponse(access_token=create_access_token(domain_user))


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
