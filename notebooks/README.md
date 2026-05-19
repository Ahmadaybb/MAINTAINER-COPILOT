# Notebooks

Training and model comparison are external Google Colab workflows. They are not part of
`docker-compose`, application startup, or CI.

Export only the inference handoff artifacts described in
`specs/001-maintainer-copilot/contracts/model-artifact.md`, then upload them to the MinIO
`models` bucket before running the modelserver.
