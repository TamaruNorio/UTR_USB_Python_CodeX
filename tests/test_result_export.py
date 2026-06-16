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
    assert summary["items"] == [{
        "antenna_number": None,
        "antenna_label": None,
        "antenna_description": None,
        "pc_uii": "E28011xxxxxxxxxxxxxx",
        "read_count": 10,
    }]


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


def test_build_result_summary_accepts_antenna_items():
    items = [{
        "antenna_number": 0,
        "antenna_label": "ANT0",
        "antenna_description": "内蔵アンテナ",
        "pc_uii": "E28011xxxxxxxxxxxxxx",
        "read_count": 2,
    }]

    summary = result_export.build_result_summary(1, 0.5, 2, {"E28011xxxxxxxxxxxxxx": 2}, "2026-06-15T12:00:00", items=items)

    assert summary["items"] == items


def test_save_results_to_csv_writes_antenna_columns(tmp_path):
    path = tmp_path / "inventory_results.csv"
    items = [{
        "antenna_number": 1,
        "antenna_label": "ANT1",
        "antenna_description": "外付けアンテナ1",
        "pc_uii": "E28011xxxxxxxxxxxxxx",
        "read_count": 1,
    }]
    summary = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00", items=items)

    result_export.save_results_to_csv(str(path), summary)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["antenna_number"] == "1"
    assert rows[0]["antenna_label"] == "ANT1"
    assert rows[0]["antenna_description"] == "外付けアンテナ1"


def test_save_results_to_csv_uses_blank_antenna_columns_when_unknown(tmp_path):
    path = tmp_path / "inventory_results.csv"
    summary = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")

    result_export.save_results_to_csv(str(path), summary)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["antenna_number"] == ""
    assert rows[0]["antenna_label"] == ""
    assert rows[0]["antenna_description"] == ""


def test_save_results_to_json_writes_null_antenna_values_when_unknown(tmp_path):
    path = tmp_path / "inventory_results.json"
    summary = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")

    result_export.save_results_to_json(str(path), summary)

    item = json.loads(path.read_text(encoding="utf-8"))[0]["items"][0]
    assert item["antenna_number"] is None
    assert item["antenna_label"] is None
    assert item["antenna_description"] is None


def test_save_results_to_csv_does_not_duplicate_header(tmp_path):
    path = tmp_path / "inventory_results.csv"
    summary1 = result_export.build_result_summary(1, 0.5, 1, {"E28011xxxxxxxxxxxxxx": 1}, "2026-06-15T12:00:00")
    summary2 = result_export.build_result_summary(2, 1.0, 3, {"E28011yyyyyyyyyyyyyy": 3}, "2026-06-15T12:01:00")

    result_export.save_results_to_csv(str(path), summary1)
    result_export.save_results_to_csv(str(path), summary2)

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = ",".join(result_export.CSV_FIELDNAMES)
    assert lines.count(header) == 1


def test_save_results_to_csv_moves_legacy_header_file(tmp_path, capsys):
    path = tmp_path / "inventory_results.csv"
    legacy_header = [
        "saved_at",
        "total_iterations",
        "total_read_time_seconds",
        "total_read_count",
        "average_read_count",
        "pc_uii",
        "read_count",
    ]
    path.write_text(
        ",".join(legacy_header)
        + "\n2026-06-15T12:00:00,1,0.5,1,1.0,E28011oldxxxxxxxxxx,1\n",
        encoding="utf-8-sig",
    )

    items = [{
        "antenna_number": 1,
        "antenna_label": "ANT1",
        "antenna_description": "外付けアンテナ1",
        "pc_uii": "E28011newxxxxxxxxxx",
        "read_count": 2,
    }]
    summary = result_export.build_result_summary(
        1,
        0.5,
        2,
        {"E28011newxxxxxxxxxx": 2},
        "2026-06-15T12:01:00",
        items=items,
    )

    result_export.save_results_to_csv(str(path), summary)

    legacy_files = list(tmp_path.glob("inventory_results_legacy_*.csv"))
    assert len(legacy_files) == 1
    legacy_lines = legacy_files[0].read_text(encoding="utf-8-sig").splitlines()
    assert legacy_lines[0].split(",") == legacy_header
    assert "E28011oldxxxxxxxxxx" in legacy_lines[1]

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["antenna_number"] == "1"
    assert rows[0]["antenna_label"] == "ANT1"
    assert rows[0]["antenna_description"] == "外付けアンテナ1"
    assert rows[0]["pc_uii"] == "E28011newxxxxxxxxxx"
    assert rows[0]["read_count"] == "2"

    captured = capsys.readouterr()
    assert "既存CSVのヘッダーが現在形式と異なるため、" in captured.out
    assert "新しいCSVヘッダーで保存を開始します。" in captured.out
