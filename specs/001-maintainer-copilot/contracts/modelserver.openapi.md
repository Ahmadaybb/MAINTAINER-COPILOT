# Contract: `modelserver` service

Internal service called only by `api` (`app/infra/modelserver_client.py`). No Anthropic key
(D2). Loads the classifier + NER artifact from MinIO and verifies SHA-256 vs. model card at
boot; refuses to serve otherwise (Principle II / D12). Safe-envelope errors.

### POST /classify
Req `{ "text": "…" }` → 200
```json
{ "label": "bug|feature|docs|question",
  "confidence": 0.0,
  "low_confidence": false,
  "model_name": "distilbert",
  "model_version": "…",
  "sha256": "…" }
```
`low_confidence` true when max softmax < configured margin (FR-004).

### POST /ner
Req `{ "text": "…" }` → 200
```json
{ "entities": [ { "text": "TypeError", "label": "error_code", "start": 12, "end": 21 } ] }
```
Labels: `repo_name`, `error_code`, `version_string`, `symbol`, `file_path` (FR-005).

### GET /healthz
200 liveness.

### GET /readyz
200 only if the artifact is downloaded and `sha256(artifact) == model_card.sha256` and the
model is loaded into memory; otherwise 503 (boot stays failed — no lazy load, D12).

**Inputs**: text is redacted-safe to log (Principle III); request/trace ids propagated from
`api`.
