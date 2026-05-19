# Model Artifacts

Training is external to this repository and happens in Google Colab. This directory is the
handoff surface for Colab-exported inference artifacts before they are uploaded to the MinIO
`models` bucket.

Expected artifacts follow `specs/001-maintainer-copilot/contracts/model-artifact.md`:

- `model.safetensors` or `model.pkl` classifier weights.
- `ner/` pipeline assets for entity extraction.
- `model_card.json` with model metadata, labels, metrics, hashes, and the classifier weight
  `sha256`.
- `mlflow_run.json` with exported metrics and parameters.

Weights and generated assets are ignored by git. Commit `model_card.json` files for review, and
the modelserver must verify the downloaded weight hash against the card before serving.
