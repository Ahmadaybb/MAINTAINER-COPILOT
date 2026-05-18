
<!--
SYNC IMPACT REPORT
==================
Version change: (uninitialized template) → 1.0.0
Bump rationale: Initial ratification — placeholders replaced with concrete,
binding principles. First adopted version.

Modified principles: N/A (all five principles newly defined from placeholders)
  - [PRINCIPLE_1] → I. Strict Layered Architecture
  - [PRINCIPLE_2] → II. Vault-Sourced Secrets & Fail-Closed Boot
  - [PRINCIPLE_3] → III. Redaction Before the Boundary
  - [PRINCIPLE_4] → IV. Evidence-Based Decisions (Golden-Set Gated)
  - [PRINCIPLE_5] → V. Defensible Code & Domain Error Mapping

Added sections:
  - Core Principles (I–V)
  - Quality Gates & CI Enforcement (was [SECTION_2])
  - Development Workflow & Review Process (was [SECTION_3])
  - Governance

Removed sections: None

Templates requiring updates:
  - .specify/templates/plan-template.md ............. ✅ updated (Constitution Check gates filled)
  - .specify/templates/spec-template.md ............. ✅ reviewed, no change required
  - .specify/templates/tasks-template.md ............ ✅ reviewed, no change required
  - .specify/templates/checklist-template.md ........ ✅ reviewed, no change required
  - .specify/templates/commands/*.md ................ N/A (directory not present)
  - README.md / docs/quickstart.md .................. N/A (not present); CLAUDE.md defers to this file

Follow-up TODOs: None — all placeholders resolved.
==================
-->

# Maintainer's Copilot Constitution

## Core Principles

### I. Strict Layered Architecture

Code MUST be organized into five layers with strictly one-directional dependencies:

- `app/api/` — HTTP concerns only (routing, request/response shaping, status codes). MUST NOT
  import SQLAlchemy, MUST NOT use Redis clients, and MUST NOT perform external or network calls
  directly.
- `app/services/` — business logic and orchestration. The only layer permitted to coordinate
  repositories, infra adapters, and domain rules.
- `app/repositories/` — SQL and persistence access only. MUST NOT raise HTTP errors and MUST NOT
  perform cache invalidation.
- `app/domain/` — Pydantic models expressing the domain. Domain models MUST remain distinct from
  SQLAlchemy ORM models; no module may pass one type where the other is expected.
- `app/infra/` — adapters for external systems (Vault, MinIO, LLM providers, tracing, cache).

Rationale: Layer leakage is the primary cause of untestable, unsecurable services. A router that
touches SQL or a repository that throws HTTP errors cannot be reasoned about, mocked, or audited
in isolation.

### II. Vault-Sourced Secrets & Fail-Closed Boot

Every secret — LLM API keys, JWT signing key, database password, MinIO credentials, tracing
keys — MUST be resolved from Vault during application startup. `.env` MUST contain only the Vault
root token and port bindings; no other secret may appear in `.env`, in source, or in container
images.

The application MUST refuse to boot when any of the following hold:

- Vault is unreachable, or a required secret is absent.
- Classifier weights are missing.
- The classifier weights' SHA-256 does not match the hash recorded in the model card.
- Any eval threshold is zero or unset.

Rationale: A service that starts in a degraded or unverified state is a security and correctness
incident waiting to happen. Failing closed at boot converts silent risk into a loud, early
failure.

### III. Redaction Before the Boundary

A redaction layer in `app/infra/` MUST process every log line, trace span, and memory write
before it leaves the service boundary. No code path may emit logs, spans, or persisted memory
that bypasses this layer.

Rationale: Secrets and user data leak through observability far more often than through features.
Centralizing redaction at the egress boundary makes the guarantee enforceable and testable rather
than aspirational.

### IV. Evidence-Based Decisions (Golden-Set Gated)

Every engineering decision affecting answer quality — embedding model, chunking strategy,
retrieval weighting, deployment choice — MUST be justified by a measured number on the golden
set. Thresholds MUST be committed in `eval_thresholds.yaml`. Any regression below a committed
threshold MUST block the CI merge. Every CI run MUST write `eval_report.json`, store it in MinIO,
and diff it against the previous green build.

Rationale: Intuition does not scale and is not reviewable. A committed number on a fixed golden
set turns "I think this is better" into a claim CI can verify and a reviewer can trust.

### V. Defensible Code & Domain Error Mapping

Every exception MUST map to a domain exception (`NotFoundError`, `PermissionDenied`,
`ToolFailure`, or another explicitly defined domain type). Stack traces MUST NOT be exposed to
users. Every uncaught exception MUST be logged with its trace ID and request ID. Tool failures in
the chatbot MUST be caught and recovered — a tool failure MUST NOT return a 500 to the user.
Prompts MUST live as version-controlled files under `prompts/`. No vibe coding: every line MUST
be understood and defensible in review.

Rationale: Users experience a system through its failures. Mapped errors, recovered tool calls,
and traceable logs are the difference between a debuggable production service and a guessing game.

## Quality Gates & CI Enforcement

- CI MUST fail the build and block merge on: any eval metric below its `eval_thresholds.yaml`
  value; any architecture-layer import violation (Principle I); or any secret detected outside
  Vault (Principle II).
- `eval_report.json` MUST be produced on every CI run, persisted to MinIO, and diffed against the
  last green build; the diff MUST be visible in the merge request.
- Boot-time validation (Vault reachability, weight presence, SHA-256 match against the model
  card, non-zero eval thresholds) MUST be covered by an automated startup test in CI.
- The redaction layer MUST have tests proving that secrets and user data are stripped from logs,
  trace spans, and memory writes.

## Development Workflow & Review Process

- Every change MUST be reviewable against these principles. Reviewers MUST reject layer leakage,
  unmapped exceptions, secrets outside Vault, un-redacted egress, and unjustified
  quality-affecting decisions.
- Architectural decisions affecting answer quality MUST cite the golden-set number in the PR
  description.
- New prompts or prompt edits MUST be committed as files under `prompts/` in the same change that
  uses them.
- Any deviation from a principle MUST be documented in the PR with explicit justification and
  carried into the plan's Complexity Tracking. Undocumented deviations block merge.

## Governance

This constitution supersedes all other development practices. Amendments MUST be proposed via
pull request, MUST include a written rationale and any required migration steps, and MUST be
approved by the project maintainers before merge.

Versioning policy (semantic):

- **MAJOR** — backward-incompatible governance change, or removal/redefinition of a principle.
- **MINOR** — a new principle or section, or materially expanded mandatory guidance.
- **PATCH** — clarifications, wording, or non-semantic refinements.

Compliance review: every PR and review MUST verify adherence to all principles above. Complexity
or deviation MUST be justified in writing. Runtime development guidance for agents lives in
`CLAUDE.md`; that file MUST remain consistent with this constitution and defers to it on any
conflict.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
