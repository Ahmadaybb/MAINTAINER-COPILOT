# Contract: `api` service

Base: `/api/v1`. Errors use the safe envelope (see README). Every response carries
`X-Request-Id`; every request is a traced span (Principle III, redacted).

## Auth & invitations

### POST /auth/jwt/login
Req `{ "email", "password" }` → 200 `{ "access_token", "token_type":"bearer" }`
| Code | When |
|------|------|
| 401 | bad credentials / inactive user |

### POST /admin/invitations  *(admin)*
Req `{ "email" }` → 201 `{ "id", "email", "expires_at" }` (raw token emailed once).
403 if caller not admin (`permission_denied`).

### POST /auth/accept-invite
Req `{ "token", "password" }` → 200 `{ "access_token" }`. 404 invalid; 410 expired/accepted.

## Triage (US1 / FR-001..FR-006)

### POST /triage
Req `{ "issue_url"?: str, "issue_text"?: str }` (exactly one).
→ 200
```json
{ "classification": { "label": "bug|feature|docs|question", "low_confidence": false },
  "entities": [ { "text": "v1.2.0", "label": "version" } ],
  "summary": "…",
  "request_id": "uuid" }
```
| Code | When |
|------|------|
| 400 | neither/both inputs (`validation_error`) |
| 422 | URL unreachable/private/deleted → message invites pasting text (US1 AC4) |
| 429 | per-maintainer rate limit (`rate_limited`, FR-032) |

Tool failures inside triage never 500 — partial result + note (FR-024).

## Chat (US3/US4/US5 — single tool-calling LLM, FR-023)

### POST /chat/sessions → 201 `{ "session_id" }`

### POST /chat/sessions/{id}/messages
Req `{ "content" }` → 200 (optionally `text/event-stream`)
```json
{ "message": { "role":"assistant", "content":"…",
   "tool_calls":[ {"name":"rag_search","ok":true} ] },
  "citations": [ { "external_ref":"docs/auth.md", "kind":"doc" } ] }
```
Tools: `classify_issue`, `extract_entities`, `summarize_issue`, `rag_search`, `write_memory`.
Ungrounded answers are flagged, not fabricated (FR-009). 429 on rate limit.

## Memory (US4/US5, FR-011/012/031/033)

| Method | Path | Role | Behavior |
|--------|------|------|----------|
| GET | /memory | owner | list own active long-term entries |
| POST | /memory | owner | explicit save → `{id}` (FR-012/013) |
| DELETE | /memory/{id} | owner | soft-delete; never recalled again (SC-013) |
| GET | /admin/memory?owner_id= | admin | inspect any (FR-018); 403 for non-admin |

No PUT — corrections via new POST that supersedes (FR-014/031).

## Widget config & knowledge source  *(admin)*

| Method | Path | Notes |
|--------|------|-------|
| POST/GET/PUT | /admin/widgets[/{id}] | theme, allowed_origins, greeting, enabled_tools, host_token_verify_key; warn on empty origins (FR-026) |
| GET | /widgets/{id}/config | public read used by widget at load; theme+greeting+enabled_tools only |
| POST | /admin/knowledge-source | connect one repo (Q1/FR-028) |
| POST | /admin/knowledge-source/sync | trigger re-sync; scheduled too (FR-029) |
| GET | /admin/knowledge-source | status: connecting/ready/syncing/error |

### POST /widget/session
Req `{ "widget_id", "host_token" }` → 200 `{ "access_token" }`.
Verifies `host_token` against `WidgetConfig.host_token_verify_key` (FR-030/D7).
401 on missing/malformed/expired token (no diagnostics).

## Health

- `GET /healthz` → 200 liveness.
- `GET /readyz` → 200 only if Vault resolved, secrets present, modelserver reachable, eval
  thresholds non-zero (Principle II / D12); else 503.
