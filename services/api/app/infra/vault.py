from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import hvac

from app.domain.errors import BootValidationError


REQUIRED_SECRET_KEYS = (
    "ANTHROPIC_API_KEY",
    "JWT_SIGNING_KEY",
    "DB_PASSWORD",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "OTEL_EXPORTER_KEY",
)


@dataclass(frozen=True, slots=True)
class AppSecrets:
    anthropic_api_key: str
    jwt_signing_key: str
    db_password: str
    minio_access_key: str
    minio_secret_key: str
    otel_exporter_key: str


class VaultClient:
    def __init__(
        self,
        *,
        addr: str | None = None,
        token: str | None = None,
        mount_point: str = "secret",
        path: str = "maintainer-copilot",
    ) -> None:
        self.addr = addr or os.getenv("VAULT_ADDR", "http://vault:8200")
        self.token = token or os.getenv("VAULT_ROOT_TOKEN")
        self.mount_point = mount_point
        self.path = path
        if not self.token:
            raise BootValidationError("Vault token is required at startup.")
        self._client = hvac.Client(url=self.addr, token=self.token)

    def read_app_secrets(self) -> AppSecrets:
        if not self._client.is_authenticated():
            raise BootValidationError("Vault is unreachable or authentication failed.")

        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=self.path,
            )
        except Exception as exc:  # noqa: BLE001 - external adapter maps to domain error.
            raise BootValidationError("Required application secrets are absent from Vault.") from exc

        data = response.get("data", {}).get("data", {})
        missing = [key for key in REQUIRED_SECRET_KEYS if not data.get(key)]
        if missing:
            raise BootValidationError("Required application secrets are absent from Vault.")

        return AppSecrets(
            anthropic_api_key=data["ANTHROPIC_API_KEY"],
            jwt_signing_key=data["JWT_SIGNING_KEY"],
            db_password=data["DB_PASSWORD"],
            minio_access_key=data["MINIO_ACCESS_KEY"],
            minio_secret_key=data["MINIO_SECRET_KEY"],
            otel_exporter_key=data["OTEL_EXPORTER_KEY"],
        )


@lru_cache(maxsize=1)
def get_vault_client() -> VaultClient:
    return VaultClient()


@lru_cache(maxsize=1)
def get_app_secrets() -> AppSecrets:
    return get_vault_client().read_app_secrets()
