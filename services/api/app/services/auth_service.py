from __future__ import annotations

from app.domain.errors import PermissionDenied
from app.domain.invitation import TokenResponse
from app.domain.user import AuthenticatedUser, UserRole
from app.infra.auth import create_access_token, verify_password
from app.repositories.db import get_sessionmaker
from app.repositories.users import UserRepository


class AuthService:
    def login(self, email: str, password: str) -> TokenResponse:
        with get_sessionmaker()() as session:
            user = UserRepository(session).get_by_email(email)
            if not user or not user.is_active or not verify_password(password, user.hashed_password):
                raise PermissionDenied("Invalid email or password.")

            domain_user = AuthenticatedUser(
                id=user.id,
                email=user.email,
                role=UserRole(user.role.value),
                is_active=user.is_active,
            )
            return TokenResponse(access_token=create_access_token(domain_user))
