# Contract: Model Artifact (Colab → repo → MinIO → modelserver)

Training is **external (Google Colab)** — not in docker-compose, not in CI. This contract is
the only handoff surface.

## Produced in Colab

- `model.safetensors` (or `model.pkl` for the TF-IDF+LogReg baseline) — classifier weights
- `ner/` — spaCy/HF NER pipeline assets
- `model_card.json`
- `mlflow_run.json` — exported MLflow run (metrics, params)

## `model_card.json` schema

```json
{
  "model_name": "distilbert",
  "version": "2026-05-18.1",
  "architecture": "distilbert-base-uncased + classification head",
  "labels": ["bug","feature","docs","question"],
  "hyperparameters": { "epochs": 3, "lr": 2e-5, "batch_size": 16 },
  "training_data_hash": "sha256:…",
  "test_split_hash": "sha256:…",
  "metrics": { "accuracy": 0.0, "macro_f1": 0.0,
               "per_class_f1": { "bug":0.0,"feature":0.0,"docs":0.0,"question":0.0 },
               "latency_ms": 0.0, "cost_usd": 0.0 },
  "sha256": "sha256 of the weights file this card describes"
}
```

`test_split_hash` MUST match across all three compared models (FR-003/SC-002).

## Placement & upload

1. Drop artifact + `model_card.json` into `models/` (weights git-ignored; `model_card.json`
   committed for review — Principle V "defensible").
2. Manually upload artifact + card to MinIO bucket `models/` **before first run**.

## modelserver boot verification (Principle II / D12)

```
download artifact + model_card.json from MinIO
computed = sha256(artifact_bytes)
assert computed == model_card.sha256        # else BootValidationError → /readyz 503, no serve
assert all eval_thresholds.yaml values > 0  # else BootValidationError
load model → /readyz 200
```

No lazy/first-request loading. A missing artifact or hash mismatch is a **boot failure**, never
a runtime 500.
