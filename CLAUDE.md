<!-- SPECKIT START -->
Active feature: **Maintainer's Copilot** (`001-maintainer-copilot`).

For technologies, project structure, architecture, and constraints, read the current plan:
`specs/001-maintainer-copilot/plan.md`
(supporting artifacts: `research.md`, `data-model.md`, `contracts/`, `quickstart.md`;
spec at `specs/001-maintainer-copilot/spec.md`; governance in
`.specify/memory/constitution.md`).

Non-negotiables: strict `app/` layering (api/services/repositories/domain/infra); all
secrets from Vault, fail-closed boot; redaction before any log/span/memory egress; every
quality choice gated by a golden-set number in `eval_thresholds.yaml`; domain-mapped
exceptions, no stack traces to users; prompts live in `prompts/`. Model training is
external (Colab) — this repo is inference-only.
<!-- SPECKIT END -->
