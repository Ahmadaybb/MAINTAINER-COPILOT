from __future__ import annotations

from pathlib import Path

from app.infra.groq import GroqClient

PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "summarize_issue.md"


class Summarizer:
    def __init__(self, client: GroqClient | None = None) -> None:
        self.client = client or GroqClient()

    async def summarize(self, issue_text: str) -> str:
        return await self.client.summarize_issue(issue_text, PROMPT_PATH)
