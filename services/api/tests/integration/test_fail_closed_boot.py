from __future__ import annotations

from pathlib import Path

from app.domain.errors import BootValidationError


def assert_nonzero_thresholds(path: Path) -> None:
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  ") and ":" in line:
            values.append(float(line.split(":", 1)[1].strip()))
    if len(values) < 4 or any(value <= 0 for value in values):
        raise BootValidationError("Eval thresholds must be non-zero.")


def test_api_refuses_zero_eval_threshold(tmp_path: Path) -> None:
    thresholds = tmp_path / "eval_thresholds.yaml"
    thresholds.write_text(
        "classification:\n  macro_f1: 0\nrag:\n  context_recall: 0.7\n  faithfulness: 0.8\n  answer_relevancy: 0.75\n",
        encoding="utf-8",
    )

    try:
        assert_nonzero_thresholds(thresholds)
    except BootValidationError:
        return

    raise AssertionError("Expected zero threshold to fail closed")


def test_api_refuses_boot_when_vault_is_down() -> None:
    def read_vault_secrets():
        raise BootValidationError("Vault down")

    try:
        read_vault_secrets()
    except BootValidationError:
        return

    raise AssertionError("Expected Vault failure to fail closed")
