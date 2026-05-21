from __future__ import annotations

from app.domain.errors import ToolFailure, UpstreamUnavailable
from app.domain.triage import Classification, Entity, TriageRequest, TriageResponse
from app.infra.github_issue import GitHubIssueClient
from app.infra.modelserver_client import ModelserverClient
from app.infra.tracing import traced_call
from app.services.summarize import Summarizer


class TriageService:
    def __init__(
        self,
        *,
        github: GitHubIssueClient | None = None,
        modelserver: ModelserverClient | None = None,
        summarizer: Summarizer | None = None,
    ) -> None:
        self.github = github or GitHubIssueClient()
        self.modelserver = modelserver or ModelserverClient()
        self.summarizer = summarizer or Summarizer()

    async def triage(self, request: TriageRequest, request_id: str) -> TriageResponse:
        issue_text = request.issue_text or ""
        if request.issue_url:
            issue_text = (await self.github.fetch_issue_thread(str(request.issue_url))).text

        notes: list[str] = []
        classification: Classification | None = None
        entities: list[Entity] = []
        summary: str | None = None

        try:
            with traced_call("tool", "classify_issue", {"issue_text": issue_text, "request_id": request_id}):
                result = await self.modelserver.classify(issue_text, request_id=request_id)
            classification = Classification.model_validate(result.model_dump())
            classification = _apply_label_safety_rules(issue_text, classification)
        except (ToolFailure, UpstreamUnavailable) as exc:
            notes.append(exc.message)

        try:
            with traced_call("tool", "extract_entities", {"issue_text": issue_text, "request_id": request_id}):
                ner_result = await self.modelserver.ner(issue_text, request_id=request_id)
            entities = [Entity.model_validate(entity.model_dump()) for entity in ner_result.entities]
        except (ToolFailure, UpstreamUnavailable) as exc:
            notes.append(exc.message)

        try:
            with traced_call("tool", "summarize_issue", {"issue_text": issue_text, "request_id": request_id}):
                summary = await self.summarizer.summarize(issue_text)
        except ToolFailure as exc:
            notes.append(exc.message)
            summary = _fallback_summary(issue_text)

        return TriageResponse(
            classification=classification,
            entities=entities,
            summary=summary,
            request_id=request_id,
            notes=notes,
        )


def _fallback_summary(issue_text: str) -> str:
    text = " ".join(issue_text.split())
    if len(text) <= 280:
        return text
    return f"{text[:277]}..."


def _apply_label_safety_rules(issue_text: str, classification: Classification) -> Classification:
    lowered = issue_text.lower()
    bug_markers = (
        "bug",
        "crash",
        "crashes",
        "error",
        "exception",
        "traceback",
        "cannot",
        "can't",
        "failed",
        "fails",
        "failure",
        "500",
        "exit code",
        "typeerror",
        "valueerror",
    )
    if classification.label != "bug" and any(marker in lowered for marker in bug_markers):
        return classification.model_copy(
            update={
                "label": "bug",
                "confidence": max(classification.confidence, 0.75),
                "low_confidence": False,
            }
        )
    return classification
