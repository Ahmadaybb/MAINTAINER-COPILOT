# Phase 0 Research: Maintainer's Copilot

**Date**: 2026-05-18 | **Plan**: [plan.md](./plan.md)

The stakeholder supplied a comprehensive stack, so most "unknowns" are **deliberately
eval-gated** decisions (Constitution Principle IV) rather than open clarifications. Each is
recorded as a decision with the metric that resolves it.

---

## D1. Service topology & layering boundary

- **Decision**: Five app services (api, chatbot, widget, modelserver, host) + db, redis, minio,
  vault, migrate in docker-compose. Constitution Principle I layering applies inside each
  Python `app/`. `chatbot` (Streamlit) and `widget` (React) are HTTP-only clients of `api`.
- **Rationale**: Keeps secrets, SQL, and external calls behind `api`/`modelserver` boundaries;
  the inference server is separable because training is external. Satisfies Principles I & II.
- **Alternatives considered**: Single monolith (rejected — mixes inference lifecycle/SHA-256
  boot with request serving, and forces the widget bundle into the API image); embedding
  inference in `api` (rejected — couples model-artifact boot failure to the whole API).

## D2. modelserver scope vs. LLM-driven summarization

- **Decision**: `modelserver` serves **only** the fine-tuned DistilBERT classifier and the NER
  pipeline (local weights from MinIO). **Summarization is LLM-driven in `api`** via
  `prompts/summarize_issue.md` calling Claude. The chat tool `summarize_issue` calls an
  api-internal summarization service, not modelserver.
- **Rationale**: Resolves the spec's "summarizer inference" vs. "summarization is LLM-driven"
  tension. Keeps the Anthropic key out of modelserver (smaller secret surface, Principle II)
  and keeps modelserver's fail-closed boot tied only to artifact + SHA-256.
- **Alternatives considered**: Summarization model in modelserver (rejected — no fine-tuned
  summarizer is trained in Colab; would need Anthropic creds in two services).

## D3. Classifier selection (3-way comparison)

- **Decision**: Train/compare in Colab: (a) fine-tuned `distilbert-base-uncased`, (b) TF-IDF +
  LogisticRegression, (c) zero-shot via claude-sonnet-4-20250514. The **served** model is the
  one with the highest **macro-F1 on the 25-item classification golden set**, subject to
  latency/cost being acceptable for ≤15 s p95 triage.
- **Rationale**: Principle IV — selection is a number, not a preference. macro-F1 chosen over
  accuracy because the 4 classes are likely imbalanced in real issue streams.
- **Resolved by**: `eval/run_classification_eval.py` → `eval_report.json`; gate in
  `eval_thresholds.yaml` (`classification.macro_f1`). Per-class F1, accuracy, latency, cost are
  recorded for auditability (spec FR-027, SC-002).
- **Alternatives considered**: Accuracy-only gate (rejected — hides minority-class collapse).

## D4. Embedding model

- **Decision**: Start with `sentence-transformers/all-MiniLM-L6-v2` (384-dim); compare against
  one alternative (e.g., `BAAI/bge-small-en-v1.5`) on the RAG golden set; keep the higher RAGAS
  context-precision/recall scorer. Embedding `model_name` is stored alongside vectors so a
  switch is a re-embed, not a schema change.
- **Rationale**: MiniLM is fast/cheap and a strong baseline; the comparison is required by
  Principle IV. Storing `model_name` makes the decision reversible and auditable.
- **Resolved by**: `eval/run_rag_eval.py` (RAGAS) → gate `rag.context_recall`,
  `rag.faithfulness`.
- **Alternatives considered**: Committing to one model with no comparison (rejected — violates
  Principle IV).

## D5. Retrieval pipeline (hybrid + rerank + HyDE)

- **Decision**: Hybrid = BM25 (sparse, `rank-bm25`) + pgvector cosine (dense), combined by a
  tunable `alpha`; cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`) on the top-K union; HyDE
  query transformation before retrieval; metadata filters (issue_type, date range,
  resolution_status). `alpha`, K, and rerank-on/off are tuned on the RAG golden set.
- **Rationale**: Hybrid + rerank is the established high-recall/high-precision pattern; HyDE
  helps terse maintainer questions. All knobs are eval-gated (Principle IV).
- **Resolved by**: RAGAS context-precision/recall on `eval/golden/rag/`; chosen `alpha`/K
  recorded in `eval_report.json`.
- **Alternatives considered**: Dense-only (rejected — weak on exact code tokens/error strings);
  naive fixed-size chunking (rejected by spec — paragraph/semantic chunking required).

## D6. Chunking

- **Decision**: Paragraph/semantic-aware chunking with heading-aware splitting for docs and
  per-comment segmentation for resolved issues; small overlap; chunk metadata carries
  `kind` (doc|resolved_issue), `issue_type`, `date`, `resolution_status`, `external_ref`.
- **Rationale**: Spec mandates non-naive chunking; metadata enables D5 filtering and citations
  (FR-008).

## D7. Authentication & embedded-widget identity handoff

- **Decision**: `fastapi-users` with JWT; signing key resolved from Vault. Roles: `user`
  (maintainer), `admin`. Invite-only: admin creates an `Invitation`; acceptance sets the
  password. **Embedded widget**: the host app passes a short-lived signed token; `api` verifies
  it against the `WidgetConfig` trust material (per-widget verification key) and mints a scoped
  session — no copilot login UI inside the iframe (spec Q2/FR-030).
- **Rationale**: Matches clarification Q2; keeps the product non-public; avoids cross-origin
  login in an iframe.
- **Alternatives considered**: Copilot login inside iframe (rejected by clarification);
  shared-cookie SSO (rejected — fails on third-party-cookie-blocking browsers).

## D8. Memory model

- **Decision**: Short-term = Redis, key per session, TTL 3600 s, holds rolling message
  window/scratch. Long-term = pgvector `long_term_memory` (episodic, explicit saves +
  inferred), embedded with the D4 model, retained **indefinitely** until owner/admin delete
  (FR-033); corrections via supersession (`superseded_by`), no in-place edit (FR-031/FR-014).
  Maintainer can list/delete own; admin can inspect all.
- **Rationale**: Directly encodes clarifications Q3 & Q5.
- **Alternatives considered**: TTL/auto-expiry on long-term memory (rejected by Q5);
  editable-in-place entries (rejected by Q3 — supersession keeps an audit trail).

## D9. Per-maintainer rate limiting

- **Decision**: Fixed-window counter in Redis keyed by user id; configurable limit/window;
  exceeding raises domain `RateLimited` → handler returns a graceful "try again shortly"
  message (Principle V, FR-032, SC-011). Counter access via `app/infra` adapter.
- **Alternatives considered**: No app-level limit (rejected by Q4); global-only limit
  (rejected — no per-user fairness/cost attribution).

## D10. Single tool-calling LLM

- **Decision**: One `claude-sonnet-4-20250514` agent with tools `classify_issue`,
  `extract_entities`, `summarize_issue`, `rag_search`, `write_memory`. Tool dispatch loop in
  `app/services/chat`. Not multi-agent, not a workflow engine (spec FR-023).
- **Rationale**: Matches spec "WHAT IT IS NOT" and stakeholder choice. Each tool maps to a
  service; tool exceptions become `ToolFailure` and are recovered in-loop (no 500, Principle V,
  FR-024).
- **Anthropic SDK note**: system prompt from `prompts/chat_system.md`; prompt-cache the static
  system + tool schema block; stream responses; classify/NER tools call `modelserver`.

## D11. Observability & redaction ordering

- **Decision**: OpenTelemetry → Jaeger; spans for every LLM call, tool call, and RAG
  retrieval. `app/infra/redaction.py` is invoked by (a) the logging formatter, (b) a span
  processor that scrubs attributes before export, and (c) the long-term-memory write path —
  redaction runs **before** the data leaves the service boundary (Principle III).
- **Rationale**: Centralized egress filter is testable; ordering guarantees no raw secret/PII
  reaches Jaeger, logs, or the memory store.

## D12. Fail-closed boot sequence

- **Decision**: On startup both `api` and `modelserver`: (1) connect Vault or abort; (2)
  resolve all required secrets or abort; (3) `modelserver` downloads the artifact from MinIO,
  parses the model card JSON, computes SHA-256, aborts on mismatch/missing; (4) load
  `eval_thresholds.yaml`, abort if any threshold is zero/unset; (5) only then bind the port and
  pass `/readyz`.
- **Rationale**: Exactly Principle II. `/readyz` reflects these checks so compose/CI can gate.
- **Alternatives considered**: Lazy artifact load on first request (rejected — turns a boot
  invariant into a runtime 500).

## D13. Knowledge ingestion (one connected repo)

- **Decision**: Admin connects one GitHub repo (public; anonymous fetch per spec assumption).
  Ingest docs (README, `/docs` globs) + closed/resolved issues → chunk (D6) → embed (D4) →
  store with metadata. Re-sync on a configurable schedule (APScheduler in `api`), incremental
  by updated-at; sync failures degrade gracefully and surface status (FR-028/029, SC-012).
- **Alternatives considered**: Manual upload (rejected by clarification Q1); webhook-driven
  (deferred — scheduled poll is simpler and sufficient at this scale).

## D14. Eval harness & CI gate

- **Decision**: Two suites — classification (macro-F1, accuracy, per-class F1, latency, cost)
  and RAG (RAGAS: faithfulness, answer relevancy, context precision/recall). CI runs both,
  writes `eval_report.json`, uploads to MinIO, diffs vs. last green build; any metric below its
  `eval_thresholds.yaml` value fails the build.
- **Rationale**: Principle IV end-to-end. Golden sets are committed (25 + 25) so results are
  reproducible and reviewable.

---

### Resolved unknowns

| Item | Status |
|------|--------|
| Embedding model choice | Eval-gated (D4) — RAGAS on golden set |
| Hybrid alpha / K / rerank | Eval-gated (D5) |
| Winning classifier | Eval-gated (D3) — macro-F1 |
| modelserver vs. LLM summarization | Resolved (D2) — modelserver = classifier+NER only |
| Widget auth | Resolved (D7) — host-signed handoff |
| Memory lifecycle | Resolved (D8) — indefinite, supersede, owner-delete |

No remaining `NEEDS CLARIFICATION`. Ready for Phase 1.
