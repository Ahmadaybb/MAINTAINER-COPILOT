---
description: "Task list for Maintainer's Copilot — executed by OpenAI Codex CLI"
---

# Tasks: Maintainer's Copilot

**Input**: Design documents in `specs/001-maintainer-copilot/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Execution runtime**: These tasks are executed by the **OpenAI Codex CLI agent**. Each task is
self-contained: it names an exact file path, one concrete action, and the design doc to consult
(referenced by repo-relative path). A fresh agent with no prior context can complete them in ID
order. Do not assume any in-memory context from planning.

**Tests**: Included where the **constitution mandates them** (redaction, fail-closed boot, eval
gates) and one integration test per user story (each story's spec "Independent Test").

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on an incomplete task)
- **[Story]**: US1–US9 for user-story phases only (none for Setup/Foundational/Polish)
- All paths are repo-relative from the project root.

## Constitution guardrails (apply to every task)

- Layering: `app/api/` HTTP only; `app/services/` logic; `app/repositories/` SQL/pgvector only
  (no HTTP errors, no cache invalidation); `app/domain/` Pydantic; `app/infra/` adapters.
- Pydantic domain models are **distinct types** from SQLAlchemy ORM models.
- Secrets only from Vault; `.env` holds only `VAULT_ROOT_TOKEN` + ports.
- Every log line / trace span / long-term-memory write passes `app/infra/redaction.py` first.
- Every exception maps to a domain exception; no stack traces to users; tool failures recover.
- Prompts are files under `prompts/`. No quality choice without a golden-set number.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create the monorepo directory skeleton from `specs/001-maintainer-copilot/plan.md` "Project Structure": `services/{api,modelserver,chatbot,widget,host}/`, `eval/golden/{classification,rag}/`, `prompts/`, `models/`, `infra/vault/`, `notebooks/`, `.github/workflows/`, with `.gitkeep` in empty dirs
- [ ] T002 [P] Create `docker-compose.yml` with services: api, chatbot, widget, modelserver, host, migrate, db (`postgres:16` + pgvector), redis (`redis:7`), minio, vault (dev mode); wire ports from env per `specs/001-maintainer-copilot/quickstart.md`
- [ ] T003 [P] Create `.env.example` containing ONLY `VAULT_ROOT_TOKEN`, `API_PORT`, `MODELSERVER_PORT`, `CHATBOT_PORT`, `WIDGET_PORT`, `HOST_PORT` (constitution Principle II)
- [ ] T004 [P] Create `eval_thresholds.yaml` with committed non-zero gates `classification.macro_f1`, `rag.context_recall`, `rag.faithfulness`, `rag.answer_relevancy` (non-zero is required for boot — `research.md` D12/D14)
- [ ] T005 [P] Create `services/api/pyproject.toml` (Python 3.11; fastapi, fastapi-users[sqlalchemy], sqlalchemy>=2, alembic, pgvector, redis, hvac, minio, sentence-transformers, rank-bm25, spacy, opentelemetry-sdk, opentelemetry-exporter-jaeger, ragas, apscheduler, pytest, httpx)
- [ ] T006 [P] Create `services/modelserver/pyproject.toml` (Python 3.11; fastapi, minio, hvac, transformers, torch, scikit-learn, spacy, opentelemetry-sdk, pytest)
- [ ] T007 [P] Create `services/chatbot/pyproject.toml` (Python 3.11; streamlit, httpx)
- [ ] T008 [P] Create `services/widget/package.json` + `services/widget/vite.config.ts` for a single-file React+Tailwind bundle per `specs/001-maintainer-copilot/contracts/widget-embed.md`
- [ ] T009 [P] Create `services/host/nginx.conf`, `services/host/index.html`, `services/host/Dockerfile` (nginx demo host embedding the widget script tag)
- [ ] T010 [P] Create `services/api/Dockerfile`, `services/modelserver/Dockerfile`, `services/chatbot/Dockerfile`, `services/widget/Dockerfile`
- [ ] T011 [P] Create placeholder prompt files `prompts/chat_system.md`, `prompts/summarize_issue.md`, `prompts/hyde.md`, `prompts/llm_classifier.md` (constitution Principle V; content finalized in T085)
- [ ] T012 [P] Create `models/README.md` summarizing `specs/001-maintainer-copilot/contracts/model-artifact.md`, and a root `.gitignore` that ignores weight files under `models/` but tracks `models/**/model_card.json`
- [ ] T013 [P] Create `notebooks/README.md` stating training is external (Google Colab) and not part of docker-compose or CI
- [ ] T014 [P] Add lint/format config: root `ruff.toml` + import-layer rules (forbid SQLAlchemy/Redis/LLM-provider imports in `**/app/api/**`), `.editorconfig`, and widget ESLint/Prettier config

**Checkpoint**: Repo scaffold builds; `docker compose config` is valid.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ No user story may start until this phase is complete.**

- [ ] T015 Create `services/api/app/domain/errors.py` defining `NotFoundError`, `PermissionDenied`, `ToolFailure`, `RateLimited`, `UpstreamUnavailable`, `ValidationError`, `BootValidationError` per `data-model.md`
- [ ] T016 Create `services/api/app/infra/vault.py` resolving all secrets at startup (`GROQ_API_KEY`, `JWT_SIGNING_KEY`, `DB_PASSWORD`, MinIO keys, OTel key) — `research.md` D12
- [ ] T017 Create `infra/vault/bootstrap.sh` that writes those secrets into Vault dev on first compose up (referenced by `docker-compose.yml`) per `quickstart.md`
- [ ] T018 Create `services/api/app/infra/redaction.py` — single egress redactor (secret/PII patterns) used by logging, tracing, and memory writes (constitution Principle III)
- [ ] T019 [P] Create `services/api/app/infra/tracing.py` — OpenTelemetry tracer + Jaeger exporter + span processor that applies `redaction.py` before export (`research.md` D11)
- [ ] T020 [P] Create `services/api/app/infra/logging.py` — structured formatter injecting `trace_id`+`request_id`, routing every record through `redaction.py`
- [ ] T021 Create `services/api/app/repositories/db.py` (SQLAlchemy 2.x engine/session, pgvector registration) and ORM declarative base under `services/api/app/repositories/models/`
- [ ] T022 Create Alembic setup `services/api/alembic/` + initial migration enabling the `vector` extension and creating `users`, `invitations` tables (`data-model.md`); make `migrate` compose service run `alembic upgrade head`
- [ ] T023 Create `services/api/app/main.py` — FastAPI app factory with fail-closed startup ordered Vault → secrets → `eval_thresholds.yaml` non-zero → modelserver `/readyz` (`research.md` D12); register exception handlers mapping domain errors to the safe envelope in `contracts/README.md`; add `/healthz` and `/readyz`
- [ ] T024 [P] Create `services/api/app/api/deps.py` — request-id middleware, auth dependency, and `user`/`admin` role guard (routers stay HTTP-only)
- [ ] T025 Create `services/api/app/infra/auth.py` (fastapi-users + JWT using Vault signing key) and `services/api/app/domain/user.py` (Pydantic) kept distinct from the ORM `User` (`data-model.md`, `research.md` D7)
- [ ] T026 Create `services/api/app/infra/modelserver_client.py` — typed HTTP client for modelserver `/classify` and `/ner` (`contracts/modelserver.openapi.md`)
- [ ] T027 Create `services/modelserver/app/main.py` (fail-closed boot) + `services/modelserver/app/infra/artifact.py` (MinIO download, SHA-256 vs `model_card.json`, `BootValidationError` on mismatch/missing) per `contracts/model-artifact.md` (D12)
- [ ] T028 [P] Create `services/modelserver/app/domain/` Pydantic request/response models for classify + NER per `contracts/modelserver.openapi.md`
- [ ] T029 Create `services/api/app/infra/redis.py` — Redis adapter for short-term-memory keyspace and rate-limit counters (used by services only)

**Checkpoint**: `api` and `modelserver` start only when all boot invariants pass; `/readyz` reflects them.

---

## Phase 3: User Story 1 — One-Shot Issue Triage (Priority: P1) 🎯 MVP

**Goal**: Authenticated maintainer pastes a GitHub issue URL or text → one response with
classification + entities + summary.
**Independent Test**: `spec.md` US1 — submit a known issue (URL and text) and verify a single
response carries label + entities + summary.

- [ ] T030 [P] [US1] Create `services/api/app/domain/triage.py` (`TriageRequest{issue_url?,issue_text?}`, `Classification`, `Entity`, `TriageResponse`) per `contracts/api.openapi.md`
- [ ] T031 [P] [US1] Create `services/api/app/infra/github_issue.py` — fetch a public GitHub issue + thread by URL anonymously; map unreachable/private/deleted to `UpstreamUnavailable` (spec US1 AC4)
- [ ] T032 [US1] Implement modelserver `/classify`: `services/modelserver/app/api/classify.py` + `services/modelserver/app/services/classifier.py` using the verified artifact; set `low_confidence` below the configured softmax margin (FR-004) per `contracts/modelserver.openapi.md`
- [ ] T033 [US1] Implement modelserver `/ner`: `services/modelserver/app/api/ner.py` + `services/modelserver/app/services/ner.py` emitting `repo_name|error_code|version_string|symbol|file_path` (FR-005)
- [ ] T034 [US1] Create `services/api/app/infra/groq.py` (Groq OpenAI-compatible chat completions client) and `services/api/app/services/summarize.py` using `prompts/summarize_issue.md` (`research.md` D2)
- [ ] T035 [US1] Implement `services/api/app/services/triage_service.py` orchestrating classify (`modelserver_client`) + NER + summarize into one `TriageResponse`; a failing sub-tool yields a partial result + note, never a 500 (FR-024)
- [ ] T036 [US1] Implement `services/api/app/api/triage.py` — `POST /triage` (auth required; 400 on neither/both inputs; 422 on unreachable URL; 429 on rate limit) per `contracts/api.openapi.md`
- [ ] T037 [US1] Implement `services/api/app/services/rate_limit.py` (Redis fixed-window per user) and apply it to `/triage`; over-limit raises `RateLimited` → graceful 429 message (FR-032, `research.md` D9)
- [ ] T038 [P] [US1] Integration test `services/api/tests/integration/test_triage.py` covering spec US1 AC1–AC4 (URL and pasted text both return label+entities+summary in one response); ALSO assert end-to-end triage latency ≤ 15 s at p95 over a repeated-request sample (SC-001) and assert a graceful 429 "try again shortly" body with no stack trace once the per-maintainer rate limit is exceeded (SC-011/FR-032)

**Checkpoint**: US1 is independently demoable — the MVP.

---

## Phase 4: User Story 2 — Authenticated Access Only (Priority: P2)

**Goal**: Only authenticated users reach any capability; roles enforced.
**Independent Test**: `spec.md` US2 — unauth blocked everywhere; maintainer denied admin action; admin allowed.

- [ ] T039 [P] [US2] Implement `services/api/app/api/auth.py` — `POST /auth/jwt/login` + logout via fastapi-users (`contracts/api.openapi.md`)
- [ ] T040 [US2] Implement `services/api/app/api/admin_invitations.py` + `services/api/app/services/invitation_service.py` + Invitation repository — admin-only `POST /admin/invitations` storing only the token hash (FR-017)
- [ ] T041 [US2] Implement `POST /auth/accept-invite` in `services/api/app/api/auth.py` with `pending→accepted` / expired→410 / accepted→404 per `data-model.md`
- [ ] T042 [US2] Apply auth + admin role guard to every copilot/admin router; refusal returns a clear message via the safe envelope (FR-015/FR-016)
- [ ] T043 [P] [US2] Integration test `services/api/tests/integration/test_auth_access.py` — unauth blocked on every capability; maintainer denied admin action; admin allowed (US2 AC1–3, SC-008, SC-010)

**Checkpoint**: Product is non-public; roles enforced.

---

## Phase 5: User Story 3 — Grounded Follow-Up Q&A / RAG (Priority: P2)

**Goal**: Grounded answers over one connected repo's docs + resolved issues, with citations.
**Independent Test**: `spec.md` US3 — answerable question cites a source; ungrounded question declines.

- [ ] T044 [P] [US3] Create domain + ORM models for `KnowledgeSource` and `DocumentChunk` (pgvector) per `data-model.md` + Alembic migration
- [ ] T045 [US3] Implement `services/api/app/api/admin_knowledge_source.py` + `services/api/app/services/knowledge_source_service.py` — `POST/GET /admin/knowledge-source`, single-repo state machine (FR-028)
- [ ] T046 [US3] Implement `services/api/app/infra/github_ingest.py` — fetch docs (README, `docs/**` globs) and closed/resolved issues from the connected repo
- [ ] T047 [US3] Implement `services/api/app/services/chunking.py` — paragraph/heading-aware chunking with metadata `kind,issue_type,date,resolution_status,external_ref` (`research.md` D6)
- [ ] T048 [US3] Implement `services/api/app/infra/embeddings.py` — `all-MiniLM-L6-v2` default, persisting `embedding_model` (`research.md` D4)
- [ ] T049 [US3] Implement `services/api/app/repositories/chunks.py` — DocumentChunk write + pgvector cosine query (SQL only; no HTTP errors)
- [ ] T050 [US3] Implement `services/api/app/services/retrieval.py` — hybrid BM25 (`rank-bm25`) + dense with tunable `alpha` + metadata filters (`research.md` D5)
- [ ] T051 [US3] Add HyDE transform (`prompts/hyde.md`) + cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`) to `services/api/app/services/retrieval.py` (`research.md` D5)
- [ ] T052 [US3] Implement `services/api/app/services/rag_service.py` — grounded answer with citations; no supporting material → explicit "no grounding" (FR-007/008/009)
- [ ] T053 [US3] Implement `services/api/app/services/sync_scheduler.py` — APScheduler incremental re-sync; failures degrade gracefully and set source status (FR-029, SC-012)
- [ ] T054 [P] [US3] Create `eval/golden/rag/` (25 question/answer/chunks triples) + `eval/run_rag_eval.py` (RAGAS) gated by `eval_thresholds.yaml` (`research.md` D14)
- [ ] T055 [P] [US3] Integration test `services/api/tests/integration/test_rag_grounded.py` — cites ≥1 source; declines when ungrounded (US3 AC1–3, SC-003)

**Checkpoint**: Grounded Q&A works against a connected repo.

---

## Phase 6: User Story 4 — Conversational Memory (Priority: P2)

**Goal**: Short-term (session) + long-term (cross-session) recall via the tool-calling chat.
**Independent Test**: `spec.md` US4 — in-session recall, cross-session recall, conflict surfaced.

- [ ] T056 [P] [US4] Create domain + ORM models `ConversationSession`, `Message`, `LongTermMemory` (pgvector) per `data-model.md` + Alembic migration
- [ ] T057 [US4] Implement `services/api/app/services/short_term_memory.py` — Redis `stm:{session_id}`, TTL 3600s (`research.md` D8)
- [ ] T058 [US4] Implement `services/api/app/api/chat.py` — `POST /chat/sessions` and `POST /chat/sessions/{id}/messages` (HTTP only)
- [ ] T059 [US4] Implement `services/api/app/services/chat_service.py` — single tool-calling Groq-backed LLM loop with tools `classify_issue, extract_entities, summarize_issue, rag_search, write_memory`; `ToolFailure` caught and recovered in-loop (no 500); system prompt `prompts/chat_system.md` (FR-023/FR-024, `research.md` D10)
- [ ] T060 [US4] Implement `services/api/app/services/long_term_memory.py` recall — pgvector similarity excluding `deleted_at`, preferring non-superseded; conflicts surface most-recent + note (FR-011/FR-014)
- [ ] T061 [P] [US4] Integration test `services/api/tests/integration/test_memory_recall.py` (US4 AC1–3); ALSO inject a failing tool (e.g., force `rag_search`/`classify_issue` to raise `ToolFailure`) mid-conversation and assert the chat loop recovers in-conversation with a graceful message and returns no 500 / no stack trace (SC-009/FR-024)

**Checkpoint**: Memory-aware conversation works.

---

## Phase 7: User Story 5 — Explicit "Remember This" + Memory Control (Priority: P2)

**Goal**: Explicit saves persist; maintainer can list/delete own entries; corrections supersede.
**Independent Test**: `spec.md` US5 — explicit remember recalled+attributed; delete → never recalled.

- [ ] T062 [US5] Implement `write_memory` tool + `POST /memory` in `services/api/app/api/memory.py` + `services/api/app/services/long_term_memory.py` (source=`explicit`, confirm stored; ambiguous request → one clarifying question) (FR-012/FR-013, US5 AC3)
- [ ] T063 [US5] Implement `GET /memory` (own active) + `DELETE /memory/{id}` (soft-delete, never recalled) + supersession on correction with no in-place edit (FR-031/FR-033, SC-013)
- [ ] T064 [P] [US5] Integration test `services/api/tests/integration/test_memory_explicit.py` (US5 AC1–4, SC-013)

**Checkpoint**: Maintainer controls their long-term memory.

---

## Phase 8: User Story 6 — Admin Widget Configuration & Embed Snippet (Priority: P2)

**Goal**: Admin creates/edits a widget config and gets a single embed snippet.
**Independent Test**: `spec.md` US6 — create→snippet; edit reflected; empty origins warned.

- [ ] T065 [P] [US6] Create domain + ORM `WidgetConfig` (theme jsonb, allowed_origins[], greeting, enabled_tools[], host_token_verify_key) + Alembic migration (`data-model.md`)
- [ ] T066 [US6] Implement `services/api/app/api/admin_widgets.py` + `services/api/app/services/widget_config_service.py` — `POST/GET/PUT /admin/widgets`; empty `allowed_origins` warning (FR-019/FR-026)
- [ ] T067 [US6] Implement embed-snippet generation (single `<script src=/widget.js data-widget-id=...>`) returned with the config (FR-020, `contracts/widget-embed.md`)
- [ ] T068 [P] [US6] Integration test `services/api/tests/integration/test_widget_config.py` (US6 AC1–3)

**Checkpoint**: Widget configs produce working snippets.

---

## Phase 9: User Story 8 — Origin Allowlist Enforced by Browser (Priority: P2)

**Goal**: Browser blocks the widget on non-allowlisted origins (CSP `frame-ancestors`).
**Independent Test**: `spec.md` US8 — allowlisted loads; non-allowlisted blocked; removal blocks new loads.

- [ ] T069 [US8] Implement `services/api/app/api/widget_public.py` — `GET /widgets/{id}/config` plus CSP `frame-ancestors` and scoped CORS derived from `allowed_origins`; empty → `'none'` (FR-022/FR-026, `contracts/widget-embed.md`)
- [ ] T070 [P] [US8] Integration test `services/api/tests/integration/test_origin_allowlist.py` asserting headers for allowlisted vs non-allowlisted origins and post-removal blocking (US8 AC1–3, SC-007)

**Checkpoint**: Embedding is origin-locked at the browser.

---

## Phase 10: User Story 7 — One-Script-Tag Embed + Host Handoff Auth (Priority: P3)

**Goal**: One script tag renders the styled widget; auth via host-signed token (no copilot login UI).
**Independent Test**: `spec.md` US7 — valid host token authenticates; invalid/expired denied; one tag only.

- [ ] T071 [US7] Implement `GET /widget.js` loader (reads `data-widget-id`, fetches config, injects iframe) in `services/api/app/api/widget_public.py` per `contracts/widget-embed.md` (FR-020)
- [ ] T072 [US7] Implement `POST /widget/session` verifying the host-signed token against `WidgetConfig.host_token_verify_key` → scoped JWT; missing/malformed/expired → 401 generic (FR-030, `research.md` D7)
- [ ] T073 [P] [US7] Build the React widget in `services/widget/src/` (Vite single-file bundle, Tailwind theme + greeting from config, `postMessage` `copilot:resize`, only `enabled_tools`) per `contracts/widget-embed.md` (FR-021)
- [ ] T074 [US7] Configure `services/host/` nginx demo to embed the snippet; ensure its origin is in the widget's `allowed_origins` (`quickstart.md`)
- [ ] T075 [P] [US7] Integration test `services/api/tests/integration/test_widget_session.py` (valid token → authenticated, no login UI; invalid/expired → denied) (US7 AC1–3, FR-030)

**Checkpoint**: End-to-end embeddable widget on the demo host.

---

## Phase 11: User Story 9 — Admin User & Memory Oversight + Streamlit UI (Priority: P3)

**Goal**: Admin invites users and inspects memory; full Streamlit chat/admin surface.
**Independent Test**: `spec.md` US9 — admin invite→user authenticates; admin inspects memory; non-admin refused.

- [ ] T076 [US9] Implement `services/api/app/api/admin_memory.py` — `GET /admin/memory?owner_id=` (admin inspect any; non-admin 403) (FR-018)
- [ ] T077 [US9] Build `services/chatbot/app.py` + `services/chatbot/pages/` (Streamlit): admin widget config, memory inspector, full chat UI — calling the `api` over HTTP only (no direct DB/Redis/secrets)
- [ ] T078 [P] [US9] Integration test `services/api/tests/integration/test_admin_oversight.py` (US9 AC1–3, SC-010)

**Checkpoint**: Admin operations and the rich UI are usable.

---

## Phase 12: Polish & Cross-Cutting Concerns

- [ ] T079 [P] Create `eval/golden/classification/` (25 hand-curated issues + labels) + `eval/run_classification_eval.py` (accuracy, macro-F1, per-class F1, latency, cost) gated by `eval_thresholds.yaml` (FR-003/FR-027/SC-002, `research.md` D3/D14)
- [ ] T080 Implement `eval/report.py` writing `eval_report.json`, uploading it to MinIO, diffing vs. the last green build, and recording an `EvalReport` row per `data-model.md` (constitution Principle IV)
- [ ] T081 Create `.github/workflows/ci.yml` — lint + unit + both eval suites; fail/block merge on any below-threshold metric, on `app/api` importing SQLAlchemy/Redis/LLM providers, or on a secret found outside Vault (constitution Quality Gates)
- [ ] T082 [P] Tests `services/api/tests/unit/test_redaction.py` and `services/modelserver/tests/test_redaction.py` proving secrets/PII are stripped from logs, spans, and memory writes (constitution Principle III)
- [ ] T083 [P] Tests `services/api/tests/integration/test_fail_closed_boot.py` and `services/modelserver/tests/test_artifact_verify.py` — refuse boot on Vault down / missing artifact / SHA-256 mismatch / zero threshold (constitution Principle II, `research.md` D12)
- [ ] T084 [P] Test `services/api/tests/integration/test_tracing_spans.py` — every LLM/tool/RAG call emits a redacted OTel span (`research.md` D11)
- [ ] T085 [P] Finalize `prompts/chat_system.md`, `prompts/summarize_issue.md`, `prompts/hyde.md`, `prompts/llm_classifier.md` and review each for defensibility (constitution Principle V)
- [ ] T086 [P] Run the `specs/001-maintainer-copilot/quickstart.md` end-to-end flow, fix gaps, and write `README.md`

---

## Dependencies & Execution Order

- **Setup (P1 tasks T001–T014)** → no dependencies; T001 first, rest [P].
- **Foundational (T015–T029)** → depends on Setup; **blocks all user stories**. Within it:
  T015 (errors) and T016 (vault) precede T023 (app factory); T021/T022 (DB) precede any ORM
  task; T025 (auth infra) precedes US2; T027 (artifact verify) precedes US1 classify/NER.
- **User stories** (after Foundational):
  - US1 (P1) — only foundational deps. **MVP.**
  - US2 (P2) — foundational (auth infra T025).
  - US3 (P2) — foundational; US3 retrieval is used by US4 chat tool `rag_search` (T059 depends on T052).
  - US4 (P2) — foundational; chat tools reuse US1 services (T032–T035) and US3 `rag_service` (T052).
  - US5 (P2) — depends on US4 long-term memory module (T060).
  - US6 (P2) — foundational only.
  - US8 (P2) — depends on US6 `WidgetConfig` (T065).
  - US7 (P3) — depends on US6 (config) and US8 (CSP/CORS).
  - US9 (P3) — depends on US4/US5 memory (inspect) and US6 (admin UI surfaces).
- **Polish (T079–T086)** → after the user stories it validates (eval/redaction/boot tests can
  start once their targets exist).

## Parallel Opportunities

- Setup: T002–T014 all [P] after T001.
- Foundational: T019/T020 [P]; T024/T028 [P] alongside their siblings.
- Within a story, [P] tasks touch different files (e.g., US1: T030, T031, T038).
- After Foundational, independent stories can run in parallel by different agents:
  US1, US2, US3, US6 have no cross-story code deps; US4→US5, US6→US8→US7, US9 are chained.

### Parallel example (US1)

```text
T030 [P][US1] services/api/app/domain/triage.py
T031 [P][US1] services/api/app/infra/github_issue.py
T038 [P][US1] services/api/tests/integration/test_triage.py
```

## Implementation Strategy

- **MVP first**: Setup → Foundational → **US1**, then STOP and validate US1 independently
  (spec US1 Independent Test). Demoable triage.
- **Incremental delivery (priority order)**: US2 → US3 → US4 → US5 → US6 → US8 → US7 → US9,
  validating each story's Independent Test before moving on.
- **Polish** continuously: redaction, fail-closed, and eval-gate tasks are constitution-
  mandated and should land with or immediately after the code they cover, not deferred.

## Notes

- Codex agent: complete tasks in ID order unless a `[P]` group is explicitly parallel; consult
  the referenced design doc before editing; keep each commit scoped to one task or `[P]` group.
- Respect the constitution guardrails block on every task — layer leakage, unmapped
  exceptions, secrets outside Vault, un-redacted egress, and ungated quality choices are merge
  blockers.
- Tests included are constitution-mandated + one integration test per user story; add more
  only if a task's acceptance needs it.
