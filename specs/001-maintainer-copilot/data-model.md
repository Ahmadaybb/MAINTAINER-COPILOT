# Phase 1 Data Model: Maintainer's Copilot

**Date**: 2026-05-18 | **Plan**: [plan.md](./plan.md)

**Constitution Principle I**: Every entity below has **two representations** — a SQLAlchemy ORM
model in `app/repositories/models/` and a distinct Pydantic domain model in `app/domain/`.
Repositories return ORM rows mapped to domain models; routers and services touch domain models
only. Vectors live in pgvector columns; short-term memory and rate counters live in Redis (no
ORM).

---

## Relational entities (PostgreSQL 16 + pgvector)

### User
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| email | citext UNIQUE NOT NULL | login identity |
| hashed_password | text | nullable until invite accepted |
| role | enum(`user`,`admin`) NOT NULL default `user` | maintainer = `user` |
| is_active | bool default true | |
| created_at | timestamptz default now() | |

Rules: email unique/normalized; only `admin` may call admin endpoints (FR-016). Deactivated
users fail auth.

### Invitation
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| email | citext NOT NULL | |
| token_hash | text NOT NULL | raw token emailed once, only hash stored |
| invited_by | UUID FK→User.id | must be admin |
| expires_at | timestamptz NOT NULL | |
| accepted_at | timestamptz NULL | |

State: `pending → accepted` (sets User.hashed_password) | `pending → expired` (now > expires_at).
Rules: FR-017; accepting a non-pending/expired invite → `NotFoundError`/`PermissionDenied`.

### ConversationSession
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | also the Redis short-term key suffix |
| user_id | UUID FK→User.id | owner |
| widget_config_id | UUID FK→WidgetConfig.id NULL | set when started via widget |
| created_at | timestamptz | |
| ended_at | timestamptz NULL | |

Short-term memory for the session is Redis `stm:{session_id}` (TTL 3600 s); DB stores metadata
+ durable transcript.

### Message
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| session_id | UUID FK→ConversationSession.id | |
| role | enum(`user`,`assistant`,`tool`) | |
| content | text | redacted before persist (Principle III) |
| tool_calls | jsonb NULL | tool name + args + result summary |
| created_at | timestamptz | |

### LongTermMemory  *(pgvector)*
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| owner_id | UUID FK→User.id | private to owner (FR-011) |
| content | text NOT NULL | redacted before write |
| embedding | vector(384) | dim follows chosen embedding model (D4) |
| embedding_model | text NOT NULL | enables reversible model swap |
| source | enum(`inferred`,`explicit`) | explicit = "remember this" (FR-012) |
| superseded_by | UUID FK→LongTermMemory.id NULL | corrections, not edits (FR-014/031) |
| created_at | timestamptz | |
| deleted_at | timestamptz NULL | soft-delete; never recalled after set (SC-013) |

State: `active → superseded` (newer fact) | `active/superseded → deleted` (owner or admin;
FR-031/033). No auto-expiry (FR-033, Q5). Recall query excludes `deleted_at IS NOT NULL` and
prefers non-superseded; conflicts surface most-recent + note (FR-014).

### KnowledgeSource
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | exactly one active row (single connected repo, Q1) |
| github_repo | text NOT NULL | `owner/name` |
| branch | text default `main` | |
| docs_globs | text[] | e.g. `README*`, `docs/**` |
| status | enum(`connecting`,`ready`,`syncing`,`error`) | |
| last_synced_at | timestamptz NULL | |
| last_error | text NULL | redacted |

State: `connecting → ready` | `ready → syncing → ready` | `* → error → syncing` (FR-028/029).

### DocumentChunk  *(pgvector)*
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| source_id | UUID FK→KnowledgeSource.id | |
| kind | enum(`doc`,`resolved_issue`) | |
| external_ref | text | doc path or issue URL (for citations, FR-008) |
| title | text | |
| content | text | one semantic/paragraph chunk (D6) |
| chunk_index | int | order within external_ref |
| issue_type | text NULL | metadata filter (D5) |
| issue_date | date NULL | date-range filter |
| resolution_status | text NULL | filter |
| embedding | vector(384) | |
| embedding_model | text NOT NULL | |

Sparse BM25 index is built in-process from `content` (D5); dense via pgvector cosine.

### WidgetConfig
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | text | |
| theme | jsonb | colors/typography for the React widget |
| allowed_origins | text[] NOT NULL | drives CORS **and** CSP `frame-ancestors` |
| greeting | text | |
| enabled_tools | text[] | subset of the 5 tools (FR-021) |
| host_token_verify_key | text NOT NULL | verifies host signed handoff (D7/FR-030) |
| created_by | UUID FK→User.id | admin |
| created_at | timestamptz | |

Rules: empty `allowed_origins` → admin warned, widget loads nowhere (FR-026, US6 AC3).

### ClassificationEvalResult
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| model_name | enum(`distilbert`,`tfidf_logreg`,`llm_zeroshot`) | |
| run_id | text | MLflow/Colab run ref |
| accuracy / macro_f1 | float | |
| per_class_f1 | jsonb | bug/feature/docs/question |
| latency_ms / cost_usd | float | |
| test_split_hash | text | identical split across models (FR-003/SC-002) |
| created_at | timestamptz | |

### EvalReport
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| kind | enum(`classification`,`rag`) | |
| commit_sha | text | |
| metrics | jsonb | |
| minio_key | text | `eval_report.json` location (Principle IV) |
| previous_report_id | UUID FK→self NULL | last green build for diff |
| passed | bool | below-threshold ⇒ false ⇒ CI blocks merge |
| created_at | timestamptz | |

### ModelArtifactRecord
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| model_name | text | |
| version | text | |
| sha256 | text NOT NULL | verified vs model card at boot (Principle II/D12) |
| model_card | jsonb | architecture, hyperparams, training-data hash, metrics |
| loaded_at | timestamptz | written only after successful verify |

---

## Redis (no ORM)

- `stm:{session_id}` → JSON rolling window/scratch. **TTL 3600 s** (D8).
- `rl:{user_id}:{window}` → integer counter for per-maintainer rate limit (D9, FR-032).

## Relationships (summary)

- User 1—N Invitation(invited_by), ConversationSession, LongTermMemory, WidgetConfig(created_by)
- ConversationSession 1—N Message
- KnowledgeSource 1—N DocumentChunk
- LongTermMemory 0..1 self (superseded_by)
- EvalReport 0..1 self (previous_report_id)

## Domain exceptions (`app/domain/errors.py`)

`NotFoundError`, `PermissionDenied`, `ToolFailure`, `RateLimited`, `UpstreamUnavailable`,
`ValidationError`, `BootValidationError` — every raised exception maps to one of these; handler
layer renders safe messages (no stack traces) and logs uncaught with trace+request id
(Principle V).
