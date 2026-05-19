#!/bin/sh
set -eu

rand() {
  tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48
}

until vault status >/dev/null 2>&1; do
  sleep 1
done

vault secrets enable -path=secret kv-v2 >/dev/null 2>&1 || true

vault kv put secret/maintainer-copilot \
  ANTHROPIC_API_KEY="$(rand)" \
  JWT_SIGNING_KEY="$(rand)" \
  DB_PASSWORD="$(rand)" \
  MINIO_ACCESS_KEY="$(rand)" \
  MINIO_SECRET_KEY="$(rand)" \
  OTEL_EXPORTER_KEY="$(rand)"
