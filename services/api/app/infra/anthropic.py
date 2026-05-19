from __future__ import annotations

from pathlib import Path

from app.domain.errors import ToolFailure
from app.infra.tracing import traced_call


class AnthropicClient:
    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        from anthropic import AsyncAnthropic
        from app.infra.vault import get_app_secrets

        self.model = model
        self._client = AsyncAnthropic(api_key=get_app_secrets().anthropic_api_key)

    async def summarize_issue(self, issue_text: str, prompt_path: Path) -> str:
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
            with traced_call("llm", "summarize_issue", {"prompt": prompt, "issue_text": issue_text}):
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=400,
                    temperature=0.0,
                    system=[
                        {
                            "type": "text",
                            "text": prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": issue_text[:12000]}],
                )
        except Exception as exc:  # noqa: BLE001 - external adapter maps provider failures.
            raise ToolFailure("The summarizer is temporarily unavailable.") from exc

        chunks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        summary = "\n".join(chunks).strip()
        if not summary:
            raise ToolFailure("The summarizer returned an empty response.")
        return summary

    async def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        try:
            with traced_call("llm", "complete", {"system_prompt": system_prompt, "user_prompt": user_prompt}):
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.0,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user_prompt}],
                )
        except Exception as exc:  # noqa: BLE001 - external adapter maps provider failures.
            raise ToolFailure("The language model is temporarily unavailable.") from exc

        chunks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(chunks).strip()
        if not text:
            raise ToolFailure("The language model returned an empty response.")
        return text
