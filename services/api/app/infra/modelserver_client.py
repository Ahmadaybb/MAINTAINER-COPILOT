from __future__ import annotations

import os
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from app.domain.errors import ToolFailure, UpstreamUnavailable


IssueLabel = Literal["bug", "feature", "docs", "question"]
EntityLabel = Literal["repo_name", "error_code", "version_string", "symbol", "file_path"]


class ClassificationResult(BaseModel):
    label: IssueLabel
    confidence: float = Field(ge=0.0, le=1.0)
    low_confidence: bool
    model_name: str
    model_version: str
    sha256: str


class Entity(BaseModel):
    text: str
    label: EntityLabel
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class NerResult(BaseModel):
    entities: list[Entity]


class ModelserverClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.base_url = (base_url or os.getenv("MODELSERVER_URL", "http://modelserver:8001")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.base_url}/readyz")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def classify(self, text: str, request_id: str | None = None) -> ClassificationResult:
        return ClassificationResult.model_validate(
            await self._post("/classify", {"text": text}, request_id=request_id)
        )

    async def ner(self, text: str, request_id: str | None = None) -> NerResult:
        return NerResult.model_validate(await self._post("/ner", {"text": text}, request_id=request_id))

    async def _post(
        self,
        path: str,
        payload: dict[str, str],
        request_id: str | None,
    ) -> dict[str, object]:
        headers = {"x-request-id": request_id} if request_id else None
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable("The modelserver is temporarily unavailable.") from exc
        if response.status_code >= 500:
            raise UpstreamUnavailable("The modelserver is temporarily unavailable.")
        if response.status_code >= 400:
            raise ToolFailure("The modelserver could not process this request.")
        return response.json()
