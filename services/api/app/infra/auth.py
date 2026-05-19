from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from collections.abc import AsyncGenerator
from typing import Any

from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.jwt import generate_jwt
from fastapi_users.password import PasswordHelper

from app.domain.user import AuthenticatedUser, UserRole
from app.infra.vault import get_app_secrets


bearer_transport = BearerTransport(tokenUrl="/api/v1/auth/jwt/login")
password_helper = PasswordHelper()


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=get_app_secrets().jwt_signing_key, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(UUIDIDMixin, BaseUserManager[AuthenticatedUser, uuid.UUID]):
    @property
    def reset_password_token_secret(self) -> str:
        return get_app_secrets().jwt_signing_key

    @property
    def verification_token_secret(self) -> str:
        return get_app_secrets().jwt_signing_key

    def parse_id(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)


async def get_user_manager() -> AsyncGenerator[UserManager, None]:
    yield UserManager(None, password_helper)  # type: ignore[arg-type]


def user_from_token_payload(payload: dict[str, object]) -> AuthenticatedUser:
    role = UserRole(str(payload.get("role", UserRole.USER)))
    return AuthenticatedUser(
        id=uuid.UUID(str(payload["sub"])),
        email=str(payload["email"]),
        role=role,
        is_active=bool(payload.get("is_active", True)),
    )


def hash_password(password: str) -> str:
    return password_helper.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    verified, _updated_hash = password_helper.verify_and_update(password, hashed_password)
    return verified


def create_access_token(user: AuthenticatedUser, lifetime_seconds: int = 3600) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "aud": ["fastapi-users:auth"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=lifetime_seconds)).timestamp()),
    }
    return generate_jwt(payload, get_app_secrets().jwt_signing_key)
