from __future__ import annotations

import json
import sys
from pathlib import Path

GOLDEN_PATH = Path(__file__).parent / "golden" / "rag" / "questions.jsonl"
THRESHOLDS_PATH = Path(__file__).parents[1] / "eval_thresholds.yaml"


def main() -> int:
    thresholds = _thresholds()
    rows = [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line]
    metrics = _score(rows)
    print(json.dumps({"kind": "rag", "metrics": metrics}, indent=2, sort_keys=True))
    failed = [
        name
        for name in ("context_recall", "faithfulness", "answer_relevancy")
        if metrics[name] < thresholds[name]
    ]
    if failed:
        print(f"RAG eval failed thresholds: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def _score(rows: list[dict]) -> dict[str, float]:
    context_hits = 0
    faithfulness_hits = 0
    relevancy_hits = 0
    for row in rows:
        expected_chunks = set(row["chunks"])
        context_ids = {context["id"] for context in row["contexts"]}
        if expected_chunks & context_ids:
            context_hits += 1
        answer_tokens = set(_tokens(row["answer"]))
        context_tokens = set(_tokens(" ".join(context["text"] for context in row["contexts"])))
        question_tokens = set(_tokens(row["question"]))
        if answer_tokens & context_tokens:
            faithfulness_hits += 1
        if answer_tokens & question_tokens or context_tokens & question_tokens:
            relevancy_hits += 1
    total = len(rows) or 1
    return {
        "context_recall": context_hits / total,
        "faithfulness": faithfulness_hits / total,
        "answer_relevancy": relevancy_hits / total,
    }


def _tokens(text: str) -> list[str]:
    return [token.strip(".,:;!?()[]{}").lower() for token in text.split() if len(token) > 2]


def _thresholds() -> dict[str, float]:
    thresholds: dict[str, float] = {}
    in_rag = False
    for line in THRESHOLDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("rag:"):
            in_rag = True
            continue
        if in_rag and line and not line.startswith(" "):
            break
        if in_rag and ":" in line:
            key, value = line.split(":", 1)
            thresholds[key.strip()] = float(value.strip())
    return thresholds


if __name__ == "__main__":
    raise SystemExit(main())
