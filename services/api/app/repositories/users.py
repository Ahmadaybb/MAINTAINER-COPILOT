from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.models.user import User, UserRole


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.lower())
        return self.session.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def create(
        self,
        *,
        email: str,
        hashed_password: str | None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        user_id: UUID | None = None,
    ) -> User:
        user = User(
            id=user_id,
            email=email.lower(),
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def set_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        self.session.flush()
        return user
