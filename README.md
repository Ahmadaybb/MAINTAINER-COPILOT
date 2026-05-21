# Maintainer's Copilot

An authenticated copilot for open-source maintainers. It triages GitHub issues, answers grounded repository questions, remembers maintainer-specific facts, and can be embedded with a single script tag.

## Services

- `services/api`: FastAPI orchestration, auth, chat, memory, RAG, widget config, admin APIs.
- `services/modelserver`: classifier and NER inference with fail-closed artifact verification.
- `services/chatbot`: Streamlit admin and chat UI that calls the API over HTTP only.
- `services/widget`: Vite React widget bundle.
- `services/host`: nginx demo host that embeds `/widget.js`.

## Quickstart

1. Copy `.env.example` to `.env` and keep only the documented Vault token and port values.
   Set `GROQ_API_KEY` in your shell before starting Vault bootstrap; do not commit it to `.env`.
2. Ensure model artifacts are available under `models/distilbert_export/` or in MinIO with a matching `model_card.json` SHA-256.
3. Start the stack:

```powershell
$env:GROQ_API_KEY="your-rotated-groq-key"
docker compose up -d vault vault-bootstrap db redis minio modelserver api chatbot widget host
```

4. Run migrations:

```bash
docker compose --profile tools run --rm migrate
```

5. Open:

- API health: `http://localhost:8000/healthz`
- Streamlit UI: `http://localhost:8501`
- Demo host: `http://localhost:8080`

## Verification

```bash
python eval/run_classification_eval.py
python eval/run_rag_eval.py
PYTHONPATH=services/api pytest services/api/tests -q
PYTHONPATH=services/modelserver pytest services/modelserver/tests -q
cd services/widget && npm ci && npm run lint && npm run build
```

The CI workflow enforces eval thresholds, redaction/fail-closed tests, widget build, architecture import guards, and a basic secret scan.

## Constitution Notes

- API routers stay HTTP-only and do not import SQLAlchemy, Redis, or LLM provider SDKs.
- Streamlit and widget clients use the API over HTTP only.
- Secrets are resolved from Vault at startup.
- Redaction runs before logs, spans, and memory persistence.
- Prompt files live under `prompts/` and are version controlled.
