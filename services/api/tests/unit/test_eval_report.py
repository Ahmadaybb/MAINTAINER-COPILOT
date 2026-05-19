from __future__ import annotations

from pathlib import Path

from eval.report import diff_metrics, write_eval_report


class FakeUploader:
    def __init__(self) -> None:
        self.calls = []

    def upload(self, path: Path, key: str) -> None:
        self.calls.append((path, key))


class FakeRepository:
    def __init__(self) -> None:
        self.rows = []

    def record(self, row) -> None:
        self.rows.append(row)


def test_eval_report_writes_uploads_diffs_and_records_row(tmp_path: Path) -> None:
    output = tmp_path / "eval_report.json"
    output.write_text('{"id":"previous","metrics":{"macro_f1":0.8}}', encoding="utf-8")
    uploader = FakeUploader()
    repository = FakeRepository()

    report = write_eval_report(
        kind="classification",
        metrics={"macro_f1": 0.9},
        passed=True,
        output_path=output,
        uploader=uploader,
        repository=repository,
    )

    assert output.exists()
    assert report["previous_report_id"] == "previous"
    assert report["diff"] == {"macro_f1": 0.09999999999999998}
    assert uploader.calls
    assert repository.rows[0].kind == "classification"
    assert repository.rows[0].passed is True


def test_diff_metrics_ignores_non_numeric_values() -> None:
    assert diff_metrics({"macro_f1": 0.9, "per_class": {}}, {"macro_f1": 0.8, "per_class": {}}) == {
        "macro_f1": 0.09999999999999998
    }
