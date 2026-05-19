Classify the issue text as exactly one label: bug, feature, docs, or question.

Definitions:
- bug: broken, crashing, regressed, incorrect, or unexpectedly failing behavior.
- feature: request for new behavior, integration, option, UI, or enhancement.
- docs: documentation, example, README, quickstart, tutorial, or API reference problem.
- question: user asks how something works, whether something is supported, or what to do.

Return JSON with:
- label
- confidence from 0.0 to 1.0
- evidence: a short quote or paraphrase from the issue text

Use only the provided issue text. If uncertain, choose the closest label and lower confidence.
