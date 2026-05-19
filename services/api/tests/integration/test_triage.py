from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import require_user
from app.api.triage import get_rate_limiter, get_triage_service
from app.domain.errors import RateLimited, UpstreamUnavailable
from app.domain.triage import Classification, Entity, TriageRequest, TriageResponse
from app.domain.user import AuthenticatedUser, UserRole
from app.main import create_app


class FakeTriageService:
    async def triage(self, request: TriageRequest, request_id: str) -> TriageResponse:
        if request.issue_url and "missing" in str(request.issue_url):
            raise UpstreamUnavailable("That issue is unreachable. Paste the issue text instead.")
        low_confidence = bool(request.issue_text and "ambiguous" in request.issue_text.lower())
        return TriageResponse(
            classification=Classification(
                label="question" if low_confidence else "bug",
                confidence=0.51 if low_confidence else 0.91,
                low_confidence=low_confidence,
                model_name="distilbert",
                model_version="test",
                sha256="abc",
            ),
            entities=[Entity(text="TypeError", label="error_code", start=0, end=9)],
            summary="The issue reports a TypeError and needs maintainer triage.",
            request_id=request_id,
        )


@dataclass
class FakeRateLimiter:
    limit: int = 1000
    count: int = 0

    def check(self, _user_id):
        self.count += 1
        if self.count > self.limit:
            raise RateLimited("Please try again shortly.")


def make_client(rate_limiter: FakeRateLimiter | None = None) -> TestClient:
    app = create_app(run_startup_checks=False)
    user = AuthenticatedUser(
        id=uuid4(),
        email="maintainer@example.com",
        role=UserRole.USER,
        is_active=True,
    )
    limiter = rate_limiter or FakeRateLimiter()
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_triage_service] = lambda: FakeTriageService()
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    return TestClient(app)


def assert_triage_payload(payload: dict) -> None:
    assert payload["classification"]["label"] in {"bug", "feature", "docs", "question"}
    assert isinstance(payload["classification"]["low_confidence"], bool)
    assert payload["entities"]
    assert payload["summary"]
    assert payload["request_id"]


def test_triage_accepts_issue_url_and_returns_single_response() -> None:
    client = make_client()
    response = client.post("/api/v1/triage", json={"issue_url": "https://github.com/org/repo/issues/1"})
    assert response.status_code == 200
    assert_triage_payload(response.json())


def test_triage_accepts_pasted_text_and_returns_single_response() -> None:
    client = make_client()
    response = client.post(
        "/api/v1/triage",
        json={"issue_text": "TypeError in parser.py on v1.2.0 when calling parse()"},
    )
    assert response.status_code == 200
    assert_triage_payload(response.json())


def test_triage_requires_exactly_one_input() -> None:
    client = make_client()
    response = client.post("/api/v1/triage", json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"

    response = client.post(
        "/api/v1/triage",
        json={"issue_url": "https://github.com/org/repo/issues/1", "issue_text": "TypeError"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_triage_unreachable_url_invites_pasting_text_without_stack_trace() -> None:
    client = make_client()
    response = client.post("/api/v1/triage", json={"issue_url": "https://github.com/org/repo/issues/missing"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "upstream_unavailable"
    assert "Paste the issue text instead" in payload["error"]["message"]
    assert "Traceback" not in response.text


def test_triage_ambiguous_issue_marks_low_confidence() -> None:
    client = make_client()
    response = client.post(
        "/api/v1/triage",
        json={"issue_text": "Ambiguous report: could be a docs request or a product question."},
    )
    assert response.status_code == 200
    assert response.json()["classification"]["low_confidence"] is True


def test_triage_rate_limit_returns_graceful_429_without_stack_trace() -> None:
    client = make_client(FakeRateLimiter(limit=2))
    for _ in range(2):
        assert client.post("/api/v1/triage", json={"issue_text": "TypeError"}).status_code == 200
    response = client.post("/api/v1/triage", json={"issue_text": "TypeError"})
    assert response.status_code == 429
    assert response.json()["error"]["message"] == "Please try again shortly."
    assert "Traceback" not in response.text


def test_triage_p95_latency_under_15_seconds_for_repeated_sample() -> None:
    client = make_client()
    latencies = []
    for _ in range(20):
        started = time.perf_counter()
        response = client.post("/api/v1/triage", json={"issue_text": "TypeError in parser.py"})
        assert response.status_code == 200
        latencies.append(time.perf_counter() - started)
    p95 = statistics.quantiles(latencies, n=20, method="inclusive")[18]
    assert p95 <= 15
