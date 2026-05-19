from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.domain.errors import BootValidationError
from app.infra.artifact import ArtifactStore, assert_nonzero_thresholds


def test_missing_artifact_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VAULT_ROOT_TOKEN", "test")
    monkeypatch.setattr("app.infra.artifact._read_minio_secrets", lambda: ("key", "secret"))

    try:
        ArtifactStore().verify_and_load()
    except BootValidationError:
        return

    raise AssertionError("Expected missing artifact to fail closed")


def test_sha256_mismatch_fails_closed(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    (tmp_path / "model_card.json").write_text(json.dumps({"sha256": "bad"}), encoding="utf-8")
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VAULT_ROOT_TOKEN", "test")
    monkeypatch.setattr("app.infra.artifact._read_minio_secrets", lambda: ("key", "secret"))

    try:
        ArtifactStore().verify_and_load()
    except BootValidationError:
        return

    raise AssertionError("Expected SHA mismatch to fail closed")


def test_valid_artifact_loads_after_hash_verify(tmp_path: Path, monkeypatch) -> None:
    weights = b"weights"
    (tmp_path / "model.safetensors").write_bytes(weights)
    (tmp_path / "model_card.json").write_text(
        json.dumps({"sha256": hashlib.sha256(weights).hexdigest(), "model_name": "distilbert"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VAULT_ROOT_TOKEN", "test")
    monkeypatch.setattr("app.infra.artifact._read_minio_secrets", lambda: ("key", "secret"))

    artifact = ArtifactStore().verify_and_load()

    assert artifact.sha256 == hashlib.sha256(weights).hexdigest()


def test_zero_threshold_fails_closed(tmp_path: Path) -> None:
    thresholds = tmp_path / "eval_thresholds.yaml"
    thresholds.write_text("classification:\n  macro_f1: 0\nrag:\n  context_recall: 0.7\n", encoding="utf-8")

    try:
        assert_nonzero_thresholds(thresholds)
    except BootValidationError:
        return

    raise AssertionError("Expected zero threshold to fail closed")
