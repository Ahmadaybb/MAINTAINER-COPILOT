from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import date

import httpx

from app.domain.errors import UpstreamUnavailable
from app.domain.knowledge import DocumentKind


@dataclass(frozen=True, slots=True)
class IngestedDocument:
    kind: DocumentKind
    external_ref: str
    title: str
    content: str
    issue_type: str | None = None
    issue_date: date | None = None
    resolution_status: str | None = None


class GitHubIngestClient:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def ingest(self, github_repo: str, branch: str, docs_globs: list[str]) -> list[IngestedDocument]:
        docs = await self._fetch_docs(github_repo, branch, docs_globs)
        issues = await self._fetch_resolved_issues(github_repo)
        return docs + issues

    async def _fetch_docs(
        self,
        github_repo: str,
        branch: str,
        docs_globs: list[str],
    ) -> list[IngestedDocument]:
        tree_url = f"https://api.github.com/repos/{github_repo}/git/trees/{branch}?recursive=1"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(tree_url, headers={"Accept": "application/vnd.github+json"})
                response.raise_for_status()
                tree = response.json().get("tree", [])
                paths = [
                    item["path"]
                    for item in tree
                    if item.get("type") == "blob" and _matches_doc_glob(item.get("path", ""), docs_globs)
                ]
                documents = []
                for path in paths:
                    raw_url = f"https://raw.githubusercontent.com/{github_repo}/{branch}/{path}"
                    raw = await client.get(raw_url)
                    raw.raise_for_status()
                    documents.append(
                        IngestedDocument(
                            kind=DocumentKind.DOC,
                            external_ref=path,
                            title=path,
                            content=raw.text,
                        )
                    )
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable("GitHub documentation ingest is temporarily unavailable.") from exc
        return documents

    async def _fetch_resolved_issues(self, github_repo: str) -> list[IngestedDocument]:
        url = f"https://api.github.com/repos/{github_repo}/issues"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    url,
                    headers={"Accept": "application/vnd.github+json"},
                    params={"state": "closed", "per_page": 50},
                )
                response.raise_for_status()
                issues = response.json()
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable("GitHub issue ingest is temporarily unavailable.") from exc

        documents = []
        for issue in issues:
            if "pull_request" in issue:
                continue
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            documents.append(
                IngestedDocument(
                    kind=DocumentKind.RESOLVED_ISSUE,
                    external_ref=str(issue.get("html_url") or ""),
                    title=str(issue.get("title") or ""),
                    content=str(issue.get("body") or ""),
                    issue_type=labels[0] if labels else None,
                    issue_date=_date_from_iso(str(issue.get("closed_at") or issue.get("created_at") or "")),
                    resolution_status="closed",
                )
            )
        return documents


def _matches_doc_glob(path: str, docs_globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in docs_globs)


def _date_from_iso(value: str) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])
