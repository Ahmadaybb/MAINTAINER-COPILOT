from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.invitation import Invitation


class InvitationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        email: str,
        token_hash: str,
        invited_by,
        expires_at: datetime,
    ) -> Invitation:
        invitation = Invitation(
            email=email.lower(),
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        self.session.flush()
        return invitation

    def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        statement = select(Invitation).where(Invitation.token_hash == token_hash)
        return self.session.execute(statement).scalar_one_or_none()

    def mark_accepted(self, invitation: Invitation, accepted_at: datetime) -> Invitation:
        invitation.accepted_at = accepted_at
        self.session.flush()
        return invitation
