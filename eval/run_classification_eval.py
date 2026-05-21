from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from report import write_eval_report

GOLDEN_PATH = Path(__file__).parent / "golden" / "classification" / "issues.jsonl"
THRESHOLDS_PATH = Path(__file__).parents[1] / "eval_thresholds.yaml"
REPORT_PATH = Path("eval_report.classification.json")


def main() -> int:
    started = time.perf_counter()
    rows = [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line]
    metrics = score(rows)
    metrics["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    metrics["cost_usd"] = round(sum(float(row.get("cost_usd", 0.0)) for row in rows), 6)
    print(json.dumps({"kind": "classification", "metrics": metrics}, indent=2, sort_keys=True))
    passed = metrics["macro_f1"] >= classification_threshold()
    write_eval_report(kind="classification", metrics=metrics, passed=passed, output_path=REPORT_PATH)
    if not passed:
        print("Classification eval failed macro-F1 threshold.", file=sys.stderr)
        return 1
    return 0


def score(rows: list[dict]) -> dict:
    labels = sorted({row["label"] for row in rows} | {row.get("prediction", "") for row in rows})
    total = len(rows) or 1
    correct = sum(1 for row in rows if row["label"] == row.get("prediction"))
    per_class = {}
    for label in labels:
        tp = sum(1 for row in rows if row["label"] == label and row.get("prediction") == label)
        fp = sum(1 for row in rows if row["label"] != label and row.get("prediction") == label)
        fn = sum(1 for row in rows if row["label"] == label and row.get("prediction") != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_class[label] = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": correct / total,
        "macro_f1": sum(per_class.values()) / (len(per_class) or 1),
        "per_class_f1": per_class,
        "support": dict(Counter(row["label"] for row in rows)),
    }


def classification_threshold() -> float:
    in_section = False
    for line in THRESHOLDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("classification:"):
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            break
        if in_section and "macro_f1:" in line:
            return float(line.split(":", 1)[1].strip())
    return 1.0


if __name__ == "__main__":
    raise SystemExit(main())
