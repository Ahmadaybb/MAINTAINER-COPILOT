from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.auth import get_auth_service, get_invitation_service
from app.api.deps import current_user
from app.domain.errors import PermissionDenied
from app.domain.invitation import InvitationRead, TokenResponse
from app.domain.user import AuthenticatedUser, UserRole
from app.main import create_app


class FakeAuthService:
    def login(self, email: str, password: str) -> TokenResponse:
        if email == "maintainer@example.com" and password == "correct":
            return TokenResponse(access_token="test-token")
        raise PermissionDenied("Invalid email or password.")


class FakeInvitationService:
    def create_invitation(self, *, email, invited_by, lifetime_hours: int = 72) -> InvitationRead:
        return InvitationRead(
            id=uuid4(),
            email=email,
            expires_at=datetime.now(UTC) + timedelta(hours=lifetime_hours),
            invite_token="raw-token-once",
        )

    def accept_invite(self, *, token: str, password: str) -> TokenResponse:
        if token == "raw-token-once" and password:
            return TokenResponse(access_token="accepted-token")
        raise PermissionDenied("Invalid invite.")


def make_client(user: AuthenticatedUser | None = None) -> TestClient:
    app = create_app(run_startup_checks=False)
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_invitation_service] = lambda: FakeInvitationService()
    if user is not None:
        app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def maintainer() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="maintainer@example.com",
        role=UserRole.USER,
        is_active=True,
    )


def admin() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


def test_login_success_and_bad_credentials_are_safe() -> None:
    client = make_client()
    response = client.post(
        "/api/v1/auth/jwt/login",
        json={"email": "maintainer@example.com", "password": "correct"},
    )
    assert response.status_code == 200
    assert response.json() == {"access_token": "test-token", "token_type": "bearer"}

    response = client.post(
        "/api/v1/auth/jwt/login",
        json={"email": "maintainer@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "permission_denied"
    assert "Traceback" not in response.text


def test_accept_invite_returns_token_without_stack_trace() -> None:
    client = make_client()
    response = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": "raw-token-once", "password": "new-password"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "accepted-token"
    assert "Traceback" not in response.text


def test_unauthenticated_user_is_blocked_from_copilot_capability() -> None:
    client = make_client()
    response = client.post("/api/v1/triage", json={"issue_text": "TypeError in parser.py"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert "Traceback" not in response.text


def test_maintainer_is_denied_admin_invitation_action() -> None:
    client = make_client(maintainer())
    response = client.post("/api/v1/admin/invitations", json={"email": "new@example.com"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert "Traceback" not in response.text


def test_admin_can_create_invitation() -> None:
    client = make_client(admin())
    response = client.post("/api/v1/admin/invitations", json={"email": "new@example.com"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "new@example.com"
    assert payload["id"]
    assert payload["expires_at"]
