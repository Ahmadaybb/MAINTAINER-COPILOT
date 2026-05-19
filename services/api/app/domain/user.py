from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class AuthenticatedUser(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool = True
