from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

REPORT_PATH = Path("eval_report.json")


@dataclass(slots=True)
class EvalReportRow:
    id: str
    kind: str
    commit_sha: str
    metrics: dict[str, Any]
    minio_key: str
    previous_report_id: str | None
    passed: bool
    created_at: str


def write_eval_report(
    *,
    kind: str,
    metrics: dict[str, Any],
    passed: bool,
    output_path: Path = REPORT_PATH,
    uploader: Any | None = None,
    repository: Any | None = None,
) -> dict[str, Any]:
    previous = _load_previous(output_path)
    report_id = str(uuid4())
    minio_key = f"eval/{kind}/{_commit_sha()}/{output_path.name}"
    row = EvalReportRow(
        id=report_id,
        kind=kind,
        commit_sha=_commit_sha(),
        metrics=metrics,
        minio_key=minio_key,
        previous_report_id=previous.get("id") if previous else None,
        passed=passed,
        created_at=datetime.now(UTC).isoformat(),
    )
    payload = {
        **asdict(row),
        "diff": diff_metrics(metrics, previous.get("metrics", {}) if previous else {}),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if uploader is not None:
        uploader.upload(output_path, minio_key)
    else:
        _upload_to_minio_if_configured(output_path, minio_key)
    if repository is not None:
        repository.record(row)
    return payload


def diff_metrics(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, float]:
    diff: dict[str, float] = {}
    for key, value in current.items():
        if isinstance(value, (int, float)) and isinstance(previous.get(key), (int, float)):
            diff[key] = float(value) - float(previous[key])
    return diff


def _load_previous(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _commit_sha() -> str:
    env_sha = os.getenv("GITHUB_SHA")
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _upload_to_minio_if_configured(path: Path, key: str) -> None:
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    if not endpoint or not access_key or not secret_key:
        return
    from minio import Minio

    client = Minio(endpoint.removeprefix("http://").removeprefix("https://"), access_key, secret_key)
    client.fput_object(os.getenv("MINIO_EVAL_BUCKET", "eval"), key, str(path))
