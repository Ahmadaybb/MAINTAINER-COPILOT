# Quickstart: Maintainer's Copilot

**Plan**: [plan.md](./plan.md) · **Prereqs**: Docker + Docker Compose; the model artifact
already produced in Colab.

## 1. Secrets (Principle II)

`.env` (copy from `.env.example`) contains **only**:

```
VAULT_ROOT_TOKEN=dev-root
API_PORT=8000
MODELSERVER_PORT=8001
CHATBOT_PORT=8501
WIDGET_PORT=5173
HOST_PORT=8080
```

No other secret goes in `.env`, source, or images. `infra/vault/bootstrap.sh` writes the real
secrets into Vault dev on first up: `GROQ_API_KEY`, `JWT_SIGNING_KEY`, `DB_PASSWORD`,
`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`, `OTEL_EXPORTER_KEY`.

## 2. Seed the model artifact (external Colab → MinIO)

Training is **not** in this repo. Before first run:

1. Run the Colab notebooks (DistilBERT fine-tune, TF-IDF+LogReg, LLM zero-shot eval).
2. Export weights + `model_card.json` (+ `mlflow_run.json`) into `models/`.
3. Upload artifact + card to MinIO bucket `models/` (see
   [contracts/model-artifact.md](./contracts/model-artifact.md)).

## 3. Bring up

```
docker compose up -d db redis minio vault
docker compose run --rm migrate            # Alembic + pgvector extension
docker compose up -d api modelserver chatbot widget host
```

Boot is **fail-closed**: `api`/`modelserver` exit if Vault is unreachable, a secret is missing,
the artifact is absent, `sha256(artifact) != model_card.sha256`, or any
`eval_thresholds.yaml` value is 0.

## 4. Verify

```
curl :8000/api/v1/readyz        # 200 only when all boot invariants pass
curl :8001/readyz               # 200 only when artifact SHA-256 verified
```

- **US1 triage**: log in, `POST /api/v1/triage` with an issue URL → one response with
  classification + entities + summary (≤15 s p95, SC-001).
- **US3 RAG**: connect a repo (`POST /admin/knowledge-source`), wait for `ready`, ask a
  question → answer cites ≥1 doc/resolved-issue (SC-003).
- **US4/5 memory**: "remember X" → new session → recalled; `DELETE /memory/{id}` → never
  recalled (SC-013).
- **US6/7/8 widget**: create a widget config (allowed_origins = host), open the nginx demo
  `host` (`:8080`) → widget renders via one script tag; open from a non-allowlisted origin →
  browser blocks the iframe (CSP `frame-ancestors`).

## 5. Evals (Principle IV)

```
python eval/run_classification_eval.py     # macro-F1 vs eval_thresholds.yaml
python eval/run_rag_eval.py                # RAGAS vs thresholds
```

CI runs both, writes `eval_report.json`, uploads to MinIO, diffs vs. last green build, and
**blocks merge** on any below-threshold metric.

## 6. Observability

Jaeger UI for traces (every LLM/tool/RAG call is a span; attributes redacted via
`app/infra/redaction.py`). Every log line carries `trace_id` + `request_id`.
