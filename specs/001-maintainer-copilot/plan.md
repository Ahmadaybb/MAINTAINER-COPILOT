# Implementation Plan: Maintainer's Copilot

**Branch**: `001-maintainer-copilot` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-maintainer-copilot/spec.md`

## Summary

An authenticated copilot that triages GitHub issues (classify → bug/feature/docs/question,
extract code-shaped entities, summarize threads in one response), answers grounded follow-up
questions via hybrid RAG over one connected repository's docs + resolved issues, carries
short-term (Redis) and long-term (pgvector) memory, and ships as a single-script-tag embeddable
React widget gated by a host-signed identity handoff and an origin allowlist.

Technical approach: a strictly layered FastAPI `api` service (api/services/repositories/
domain/infra) orchestrates a single tool-calling Claude model; a separate FastAPI `modelserver`
serves the fine-tuned classifier + NER, loading its artifact from MinIO and verifying SHA-256
against the model card at boot (fail-closed, Principle II). All quality decisions
(embedding model, hybrid alpha, winning classifier) are decided by numbers on committed golden
sets and gated in CI (Principle IV). Model training is **external (Google Colab)** — this repo
is inference-only and contains no training infrastructure.

## Technical Context

**Language/Version**: Python 3.11+ (`api`, `modelserver`, `chatbot`); TypeScript/React via
Vite (`widget`); SQL (PostgreSQL 16 + pgvector)

**Primary Dependencies**: FastAPI, fastapi-users (JWT), SQLAlchemy 2.x + Alembic, pgvector,
redis-py, hvac (Vault), minio, anthropic (claude-sonnet-4-20250514), sentence-transformers
(all-MiniLM-L6-v2 + one alternative for comparison), rank-bm25, cross-encoder
(ms-marco-MiniLM-L-6-v2), spaCy/HF NER pipeline, OpenTelemetry SDK + Jaeger exporter, RAGAS,
Streamlit; Vite + React + Tailwind for the widget; nginx for the demo host

**Storage**: PostgreSQL 16 with pgvector (relational + dense vectors, long-term memory, chunks,
eval results); Redis 7 (short-term session memory TTL=3600s, per-maintainer rate-limit
counters); MinIO (model artifacts, `eval_report.json`); HashiCorp Vault dev (all secrets)

**Testing**: pytest (unit/integration/contract) for Python services; Vitest + React Testing
Library for the widget; golden-set eval suites (classification macro-F1, RAGAS) run in CI

**Target Platform**: Linux containers via docker-compose (services: api, chatbot, widget,
modelserver, host, migrate, db, redis, minio, vault)

**Project Type**: Multi-service web system (backend API + inference server + admin UI +
embeddable front-end widget + demo host)

**Performance Goals**: One-shot triage end-to-end ≤ 15 s p95 (SC-001); grounded answers cite ≥1
source ≥90% (SC-003); scheduled corpus re-sync completes within one interval ≥99% (SC-012)

**Constraints**: Fail-closed boot (Vault reachable, classifier weights present, SHA-256 ==
model card, no zero eval thresholds); `.env` holds only Vault root token + ports; redaction
before any log/span/memory egress; tool failures never 500 to the user; prompts are files under
`prompts/`

**Scale/Scope**: Single-project deployment, invite-only; tens of maintainers, low concurrency;
one connected GitHub repo; ~50–500 docs/resolved-issue chunks; 25-item classification golden
set + 25-triple RAG golden set

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Derived from `.specify/memory/constitution.md` v1.0.0:

- **Layering (I)** — ✅ PASS. `api` and `modelserver` use `app/api` (routers, HTTP only) →
  `app/services` (orchestration) → `app/repositories` (SQL/pgvector only) → `app/domain`
  (Pydantic) with `app/infra` adapters (Vault, MinIO, Redis, Anthropic, modelserver client,
  GitHub ingest, embeddings, reranker, tracing, redaction). Routers never import SQLAlchemy/
  Redis/Anthropic and make no external calls; repositories raise no HTTP errors and do no cache
  invalidation; Pydantic domain models are separate types from SQLAlchemy ORM models. The
  Streamlit `chatbot` talks only to the `api` over HTTP (no direct DB/Redis).
- **Secrets & Fail-Closed Boot (II)** — ✅ PASS. `app/infra/vault.py` resolves every secret
  (Anthropic key, JWT signing key, DB password, MinIO creds, OTel/Jaeger keys) at startup.
  `api` and `modelserver` refuse to boot if Vault is unreachable, a required secret is absent,
  classifier weights are missing, the artifact SHA-256 ≠ model card, or any threshold in
  `eval_thresholds.yaml` is zero/unset. `.env.example` documents only `VAULT_ROOT_TOKEN` and
  port bindings.
- **Redaction (III)** — ✅ PASS. `app/infra/redaction.py` is the single egress filter; logging
  formatter, the OTel span processor, and the long-term-memory write path all route through it.
  Tested to strip secrets/PII from logs, spans, and memory writes.
- **Evidence-Based (IV)** — ✅ PASS. Embedding model (MiniLM vs. one alternative), hybrid alpha,
  reranking on/off, and the winning classifier are decided by numbers on the committed golden
  sets. `eval_thresholds.yaml` gates macro-F1 (classification) and RAGAS (RAG); CI writes
  `eval_report.json`, stores it in MinIO, and diffs vs. the last green build.
- **Defensible Code (V)** — ✅ PASS. `app/domain/errors.py` defines `NotFoundError`,
  `PermissionDenied`, `ToolFailure`, `RateLimited`, `UpstreamUnavailable`, `BootValidationError`;
  an exception-handler layer maps all to safe responses (no stack traces) and logs uncaught
  errors with trace ID + request ID. The chatbot tool loop catches `ToolFailure` and recovers
  in-conversation. All prompts (`chat_system`, `summarize_issue`, `hyde`, `llm_classifier`)
  live under `prompts/`.

**Result**: PASS — no violations. Complexity Tracking is empty. The `api`/`modelserver` split
is **required by** Principle II + the external-training constraint (inference-only repo), not a
deviation from it.

## Project Structure

### Documentation (this feature)

```text
specs/001-maintainer-copilot/
├── plan.md              # This file
├── spec.md              # Feature specification (with Clarifications)
├── research.md          # Phase 0 output — decisions, rationale, alternatives
├── data-model.md        # Phase 1 output — entities, relationships, state
├── quickstart.md        # Phase 1 output — bring-up & verification
├── contracts/           # Phase 1 output — API / widget / artifact contracts
│   ├── README.md
│   ├── api.openapi.md
│   ├── modelserver.openapi.md
│   ├── widget-embed.md
│   └── model-artifact.md
└── checklists/
    └── requirements.md  # Spec quality checklist (from /speckit.specify)
```

### Source Code (repository root)

```text
docker-compose.yml                 # api, chatbot, widget, modelserver, host, migrate, db, redis, minio, vault
.env.example                       # ONLY VAULT_ROOT_TOKEN + ports (Principle II)
eval_thresholds.yaml               # committed gates: classification macro-F1, RAGAS (Principle IV)
.github/workflows/ci.yml           # runs eval suites; blocks merge on regression
models/                            # Colab-exported artifact lands here; model card tracked
└── README.md                      # artifact contract; weights are git-ignored, fetched from MinIO
prompts/                           # version-controlled prompts (Principle V)
├── chat_system.md
├── summarize_issue.md
├── hyde.md
└── llm_classifier.md
notebooks/README.md                # pointer to external Colab training (NOT run in compose)
infra/vault/bootstrap.sh           # writes secrets into Vault dev on first run

services/
├── api/                           # FastAPI — auth, chat, memory, RAG, widget config
│   ├── app/
│   │   ├── api/                   # routers — HTTP only
│   │   ├── services/              # chat orchestration, RAG pipeline, memory, triage,
│   │   │                          #   widget config, ingestion, eval
│   │   ├── repositories/          # SQL + pgvector access only
│   │   ├── domain/                # Pydantic models + errors.py (domain exceptions)
│   │   ├── infra/                 # vault, minio, redis, anthropic, modelserver_client,
│   │   │                          #   github_ingest, embeddings, reranker, tracing,
│   │   │                          #   redaction.py
│   │   ├── bootstrap.py           # Vault resolve + fail-closed boot checks
│   │   └── main.py                # app factory, exception handlers, OTel wiring
│   ├── alembic/                   # migrations (run by `migrate` service)
│   ├── tests/{unit,integration,contract}/
│   ├── Dockerfile
│   └── pyproject.toml
├── modelserver/                   # FastAPI — classifier + NER inference (no training)
│   ├── app/{api,services,domain,infra}/
│   │   └── infra/artifact.py      # MinIO load + SHA-256 verify vs model card (fail-closed)
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── chatbot/                       # Streamlit — admin config, memory inspector, full chat
│   ├── app.py
│   ├── pages/
│   ├── Dockerfile
│   └── pyproject.toml
├── widget/                        # Vite + React — single bundled JS + /widget.js loader
│   ├── src/
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── package.json
└── host/                          # nginx demo host app (embeds the widget)
    ├── nginx.conf
    ├── index.html
    └── Dockerfile

eval/
├── golden/classification/         # 25 hand-curated issues + labels
├── golden/rag/                    # 25 question/answer/chunks triples
├── run_classification_eval.py
└── run_rag_eval.py                # RAGAS
```

**Structure Decision**: Multi-service monorepo under `services/`. Constitution Principle I
layering is applied **inside** each Python service's `app/` (`api` fully; `modelserver` with
`api/services/domain/infra` — no `repositories` since it owns no SQL, only a MinIO-loaded
artifact). The Streamlit `chatbot` and React `widget` are pure clients of `api` (no direct DB/
Redis/secret access), preserving the boundary. Training code is intentionally absent: `models/`
is the only handoff surface and the artifact is pulled from MinIO at runtime.

## Complexity Tracking

> No constitution violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | —          | —                                    |

Note: The number of services (api, chatbot, widget, modelserver, host, plus db/redis/minio/
vault/migrate) is driven directly by spec requirements (embeddable widget, admin UI, grounded
RAG, external-training inference boundary) and the constitution's fail-closed/secret rules — it
is not incidental complexity and requires no justification entry.
