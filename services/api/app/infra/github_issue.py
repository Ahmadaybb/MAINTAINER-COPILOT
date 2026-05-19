from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.domain.errors import UpstreamUnavailable, ValidationError

GITHUB_ISSUE_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$")


@dataclass(frozen=True, slots=True)
class GitHubIssueThread:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    comments: list[str]

    @property
    def text(self) -> str:
        parts = [f"Repository: {self.owner}/{self.repo}", f"Issue #{self.number}: {self.title}", self.body]
        parts.extend(f"Comment: {comment}" for comment in self.comments)
        return "\n\n".join(part for part in parts if part)


class GitHubIssueClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_issue_thread(self, issue_url: str) -> GitHubIssueThread:
        match = GITHUB_ISSUE_RE.match(issue_url)
        if not match:
            raise ValidationError("Provide a valid public GitHub issue URL.")

        owner, repo, number_text = match.groups()
        number = int(number_text)
        issue_api = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        comments_api = f"{issue_api}/comments"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                issue_response = await client.get(issue_api, headers={"Accept": "application/vnd.github+json"})
                if issue_response.status_code in {403, 404, 410}:
                    raise UpstreamUnavailable("That issue is unreachable. Paste the issue text instead.")
                issue_response.raise_for_status()
                issue = issue_response.json()
                comments_response = await client.get(
                    comments_api,
                    headers={"Accept": "application/vnd.github+json"},
                    params={"per_page": 100},
                )
                comments_response.raise_for_status()
                comments_payload = comments_response.json()
        except UpstreamUnavailable:
            raise
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable("That issue is unreachable. Paste the issue text instead.") from exc

        if "pull_request" in issue:
            raise UpstreamUnavailable("That issue is unreachable. Paste the issue text instead.")

        comments = [str(item.get("body") or "") for item in comments_payload]
        return GitHubIssueThread(
            owner=owner,
            repo=repo,
            number=number,
            title=str(issue.get("title") or ""),
            body=str(issue.get("body") or ""),
            comments=comments,
        )
