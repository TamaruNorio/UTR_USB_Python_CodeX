import csv
import json

import src.utr_result_export as result_export


def test_build_result_summary_calculates_average_read_count():
    summary = result_export.build_result_summary(
        total_iterations=4,
        total_read_time=1.25,
        total_read_count=10,
        pc_uii_count_dict={"E28011xxxxxxxxxxxxxx": 10},
        saved_at="2026-06-15T12:00:00",
    )

    assert summary["average_read_count"] == 2.5
    assert summary["items"] == [{"pc_uii": "E28011xxxxxxxxxxxxxx", "read_count": 10}]


def test_build_result_summary_uses_zero_average_when_iterations_are_zero():
    summary = result_export.build_result_summary(
        total_iterations=0,
        total_read_time=0.0,
        total_read_count=0,
        pc_uii_count_dict={},
        saved_at="2026-06-15T12:00:00",
    )

    assert summary["average_read_count"] == 0.0


def test_save_results_to_json_creates_history_list(tmp_path):
    path = tmp_path / "inventory_results.json"
    summary = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")

    result_export.save_results_to_json(str(path), summary)

    assert json.loads(path.read_text(encoding="utf-8")) == [summary]


def test_save_results_to_json_appends_history(tmp_path):
    path = tmp_path / "inventory_results.json"
    summary1 = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")
    summary2 = result_export.build_result_summary(2, 1.0, 3, {"E28011yyyyyyyyyyyyyy": 3}, "2026-06-15T12:01:00")

    result_export.save_results_to_json(str(path), summary1)
    result_export.save_results_to_json(str(path), summary2)

    history = json.loads(path.read_text(encoding="utf-8"))
    assert len(history) == 2
    assert history[0] == summary1
    assert history[1] == summary2


def test_save_results_to_csv_writes_header(tmp_path):
    path = tmp_path / "inventory_results.csv"
    summary = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")

    result_export.save_results_to_csv(str(path), summary)

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].split(",") == result_export.CSV_FIELDNAMES


def test_save_results_to_csv_writes_pc_uii_and_read_count(tmp_path):
    path = tmp_path / "inventory_results.csv"
    summary = result_export.build_result_summary(1, 0.5, 2, {"E28011xxxxxxxxxxxxxx": 2}, "2026-06-15T12:00:00")

    result_export.save_results_to_csv(str(path), summary)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["pc_uii"] == "E28011xxxxxxxxxxxxxx"
    assert rows[0]["read_count"] == "2"


def test_save_results_to_csv_does_not_duplicate_header(tmp_path):
    path = tmp_path / "inventory_results.csv"
    summary1 = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")
    summary2 = result_export.build_result_summary(2, 1.0, 3, {"E28011yyyyyyyyyyyyyy": 3}, "2026-06-15T12:01:00")

    result_export.save_results_to_csv(str(path), summary1)
    result_export.save_results_to_csv(str(path), summary2)

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = ",".join(result_export.CSV_FIELDNAMES)
    assert lines.count(header) == 1
