from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.domain.errors import ToolFailure
from app.infra.tracing import traced_call

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


class GroqClient:
    def __init__(self, model: str = DEFAULT_GROQ_MODEL, base_url: str = GROQ_CHAT_COMPLETIONS_URL) -> None:
        from app.infra.vault import get_app_secrets

        self.model = model
        self.base_url = base_url
        self.api_key = get_app_secrets().groq_api_key

    async def summarize_issue(self, issue_text: str, prompt_path: Path) -> str:
        prompt = prompt_path.read_text(encoding="utf-8")
        try:
            with traced_call("llm", "summarize_issue", {"prompt": prompt, "issue_text": issue_text}):
                text = await self._complete(
                    system_prompt=prompt,
                    user_prompt=issue_text[:12000],
                    max_tokens=400,
                )
        except Exception as exc:  # noqa: BLE001 - external adapter maps provider failures.
            raise ToolFailure("The summarizer is temporarily unavailable.") from exc
        if not text:
            raise ToolFailure("The summarizer returned an empty response.")
        return text

    async def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        try:
            with traced_call("llm", "complete", {"system_prompt": system_prompt, "user_prompt": user_prompt}):
                text = await self._complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                )
        except Exception as exc:  # noqa: BLE001 - external adapter maps provider failures.
            raise ToolFailure("The language model is temporarily unavailable.") from exc
        if not text:
            raise ToolFailure("The language model returned an empty response.")
        return text

    async def _complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
