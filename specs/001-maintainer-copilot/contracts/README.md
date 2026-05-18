# Contracts: Maintainer's Copilot

Interface contracts for the feature. All HTTP errors use the safe envelope (Principle V) — no
stack traces:

```json
{ "error": { "code": "not_found|permission_denied|rate_limited|tool_failure|validation_error|upstream_unavailable",
             "message": "human, non-technical",
             "request_id": "uuid", "trace_id": "hex" } }
```

| Contract | Surface |
|----------|---------|
| [api.openapi.md](./api.openapi.md) | `api` service — auth, chat, triage, memory, widget config, ingestion, health |
| [modelserver.openapi.md](./modelserver.openapi.md) | `modelserver` — classify, NER, health |
| [widget-embed.md](./widget-embed.md) | `/widget.js` loader, iframe, postMessage, host identity handoff, CSP/CORS |
| [model-artifact.md](./model-artifact.md) | Colab → `models/` → MinIO artifact + model-card contract |

Auth: Bearer JWT (HS/RS key from Vault) for direct/Streamlit clients; widget sessions are
minted from a verified host-signed token. Roles: `user` (maintainer), `admin`.
