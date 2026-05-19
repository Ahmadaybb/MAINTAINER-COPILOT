from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.errors import BootValidationError


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    model_name: str
    version: str
    sha256: str
    weights: bytes
    model_card: dict[str, Any]
    artifact_dir: Path | None = None


class ArtifactStore:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        bucket: str = "models",
        weights_key: str = "model.safetensors",
        card_key: str = "model_card.json",
    ) -> None:
        endpoint_url = endpoint or os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        self.endpoint = endpoint_url.removeprefix("http://").removeprefix("https://")
        self.secure = endpoint_url.startswith("https://")
        self.bucket = bucket
        self.weights_key = weights_key
        self.card_key = card_key

    def verify_and_load(self) -> ModelArtifact:
        local_dir = os.getenv("MODEL_ARTIFACT_DIR")
        if local_dir:
            _read_minio_secrets()
            return self._verify_local(Path(local_dir))

        access_key, secret_key = _read_minio_secrets()
        from minio import Minio

        client = Minio(self.endpoint, access_key=access_key, secret_key=secret_key, secure=self.secure)
        try:
            card_bytes = _read_object(client, self.bucket, self.card_key)
            weights = _read_object(client, self.bucket, self.weights_key)
        except Exception as exc:  # noqa: BLE001 - external adapter maps to domain error.
            raise BootValidationError("Model artifact or model card is missing.") from exc

        try:
            model_card = json.loads(card_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise BootValidationError("Model card is invalid JSON.") from exc

        return _verify_weights(weights=weights, model_card=model_card, artifact_dir=None)

    def _verify_local(self, artifact_dir: Path) -> ModelArtifact:
        weights_path = artifact_dir / self.weights_key
        card_path = artifact_dir / self.card_key
        if not weights_path.exists() or not card_path.exists():
            raise BootValidationError("Model artifact or model card is missing.")
        try:
            model_card = json.loads(card_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BootValidationError("Model card is invalid JSON.") from exc
        return _verify_weights(
            weights=weights_path.read_bytes(),
            model_card=model_card,
            artifact_dir=artifact_dir,
        )


def assert_nonzero_thresholds(path: Path | None = None) -> None:
    threshold_path = path or Path(os.getenv("EVAL_THRESHOLDS_PATH", "/eval_thresholds.yaml"))
    if not threshold_path.exists():
        threshold_path = Path(__file__).resolve().parents[4] / "eval_thresholds.yaml"
    if not threshold_path.exists():
        raise BootValidationError("Eval thresholds are required at startup.")
    values = [
        float(line.split(":", 1)[1].strip())
        for line in threshold_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("  ") and ":" in line
    ]
    if len(values) < 4 or any(value <= 0 for value in values):
        raise BootValidationError("Eval thresholds must be non-zero.")


def _verify_weights(
    *,
    weights: bytes,
    model_card: dict[str, Any],
    artifact_dir: Path | None,
) -> ModelArtifact:
    expected = _expected_sha256(model_card)
    computed = hashlib.sha256(weights).hexdigest()
    if expected != computed:
        raise BootValidationError("Model artifact SHA-256 does not match the model card.")
    return ModelArtifact(
        model_name=str(model_card.get("deployment_choice") or model_card.get("model_name", "unknown")),
        version=str(model_card.get("version") or model_card.get("base_model", "unknown")),
        sha256=computed,
        weights=weights,
        model_card=model_card,
        artifact_dir=artifact_dir,
    )


def _expected_sha256(model_card: dict[str, Any]) -> str:
    value = model_card.get("sha256") or model_card.get("artifact", {}).get("sha256")
    return str(value or "").removeprefix("sha256:")


def _read_object(client: Minio, bucket: str, key: str) -> bytes:
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _read_minio_secrets() -> tuple[str, str]:
    import hvac

    token = os.getenv("VAULT_ROOT_TOKEN")
    if not token:
        raise BootValidationError("Vault token is required at startup.")
    client = hvac.Client(url=os.getenv("VAULT_ADDR", "http://vault:8200"), token=token)
    if not client.is_authenticated():
        raise BootValidationError("Vault is unreachable or authentication failed.")
    try:
        response = client.secrets.kv.v2.read_secret_version(
            mount_point="secret",
            path="maintainer-copilot",
        )
    except Exception as exc:  # noqa: BLE001 - external adapter maps to domain error.
        raise BootValidationError("Required MinIO secrets are absent from Vault.") from exc
    data = response.get("data", {}).get("data", {})
    access_key = data.get("MINIO_ACCESS_KEY")
    secret_key = data.get("MINIO_SECRET_KEY")
    if not access_key or not secret_key:
        raise BootValidationError("Required MinIO secrets are absent from Vault.")
    return str(access_key), str(secret_key)
