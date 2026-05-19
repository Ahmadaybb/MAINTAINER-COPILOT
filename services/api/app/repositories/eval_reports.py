from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.models.eval import EvalKind, EvalReport


class EvalReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        kind: str,
        commit_sha: str,
        metrics: dict,
        minio_key: str,
        previous_report_id: UUID | None,
        passed: bool,
    ) -> EvalReport:
        report = EvalReport(
            kind=EvalKind(kind),
            commit_sha=commit_sha,
            metrics=metrics,
            minio_key=minio_key,
            previous_report_id=previous_report_id,
            passed=passed,
        )
        self.session.add(report)
        self.session.flush()
        return report
