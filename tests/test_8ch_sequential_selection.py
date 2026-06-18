#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""8CH順次Inventory向けの選択順テスト。"""

import csv
import json

from src.utr_8ch import build_8ch_inventory_targets, parse_8ch_inventory_selection_input
from src.utr_8ch_sequential_inventory_cli import (
    _append_8ch_summary_to_csv,
    _append_8ch_summary_to_json,
    _build_8ch_sequential_inventory_summary,
    _parse_restore_usage_antenna_target_input,
)
from src.utr_antenna import AntennaCheckTarget


def test_parse_8ch_inventory_selection_input_preserves_selected_order():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
        AntennaCheckTarget(0x04, "ANT5", "外付けアンテナ"),
    ])

    selected = parse_8ch_inventory_selection_input(targets, "5,1,3")

    assert selected == [targets[2], targets[0], targets[1]]


def test_parse_8ch_inventory_selection_input_all_keeps_candidate_order():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])

    assert parse_8ch_inventory_selection_input(targets, "all") == targets


def test_parse_restore_usage_antenna_target_input_uses_selected_candidates_only():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])

    assert _parse_restore_usage_antenna_target_input(targets, "3") == targets[1]

    try:
        _parse_restore_usage_antenna_target_input(targets, "2")
    except ValueError as exc:
        assert "候補に表示されているANT番号" in str(exc)
    else:
        raise AssertionError("ANT2 must be rejected because it is not a selected candidate")


def test_parse_restore_usage_antenna_target_input_rejects_multiple_targets():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])

    try:
        _parse_restore_usage_antenna_target_input(targets, "1,3")
    except ValueError as exc:
        assert "複数指定" in str(exc)
    else:
        raise AssertionError("multiple restore targets must be rejected")


def test_parse_restore_usage_antenna_target_input_q_cancels_restore():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
    ])

    assert _parse_restore_usage_antenna_target_input(targets, "q") is None


def test_parse_restore_usage_antenna_target_input_rejects_all():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])

    try:
        _parse_restore_usage_antenna_target_input(targets, "all")
    except ValueError as exc:
        assert "all は使用できません" in str(exc)
    else:
        raise AssertionError("all must be rejected for restore target selection")


def test_build_8ch_sequential_inventory_summary_keeps_ant_order_and_counts():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])

    summary = _build_8ch_sequential_inventory_summary(
        selected_targets=targets,
        total_inventory_attempts=4,
        total_read_time=0.5555,
        total_read_count=29,
        ant_read_counts={"ANT1": 2, "ANT3": 27},
        ant_inventory_counts={"ANT1": 2, "ANT3": 2},
        ant_skip_counts={"ANT1": 0, "ANT3": 0},
        last_used_antenna_label="ANT3",
        restore_result={
            "requested": True,
            "target_label": "ANT1",
            "success": True,
            "message": "戻し完了: ANT1 / 使用アンテナ番号 00h",
        },
        saved_at="2026-06-18T09:00:00",
    )

    assert summary["selected_order"] == ["ANT1", "ANT3"]
    assert summary["total_inventory_attempts"] == 4
    assert summary["total_read_time_seconds"] == round(0.5555, 3)
    assert summary["total_read_count"] == 29
    assert summary["last_used_antenna_label"] == "ANT3"
    assert summary["restore"]["target_label"] == "ANT1"
    assert summary["privacy_note"] == "PC+UII values are not stored in this 8CH summary."
    assert summary["ant_results"] == [
        {
            "antenna_label": "ANT1",
            "physical_port": 1,
            "usage_antenna_number": "00h",
            "inventory_count": 2,
            "read_count": 2,
            "skip_count": 0,
        },
        {
            "antenna_label": "ANT3",
            "physical_port": 3,
            "usage_antenna_number": "40h",
            "inventory_count": 2,
            "read_count": 27,
            "skip_count": 0,
        },
    ]


def test_append_8ch_summary_to_csv_writes_ant_summary_rows(tmp_path):
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"),
    ])
    summary = _build_8ch_sequential_inventory_summary(
        selected_targets=targets,
        total_inventory_attempts=4,
        total_read_time=0.56,
        total_read_count=29,
        ant_read_counts={"ANT1": 2, "ANT3": 27},
        ant_inventory_counts={"ANT1": 2, "ANT3": 2},
        ant_skip_counts={"ANT1": 0, "ANT3": 0},
        last_used_antenna_label="ANT3",
        restore_result={"requested": False, "target_label": None, "success": None, "message": "not_requested"},
        saved_at="2026-06-18T09:00:00",
    )
    path = tmp_path / "8ch_summary.csv"

    _append_8ch_summary_to_csv(str(path), summary)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert rows[0]["selected_order"] == "ANT1 -> ANT3"
    assert rows[0]["antenna_label"] == "ANT1"
    assert rows[0]["usage_antenna_number"] == "00h"
    assert rows[0]["read_count"] == "2"
    assert rows[1]["antenna_label"] == "ANT3"
    assert rows[1]["usage_antenna_number"] == "40h"
    assert rows[1]["read_count"] == "27"


def test_append_8ch_summary_to_json_appends_history_without_pc_uii(tmp_path):
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
    ])
    summary = _build_8ch_sequential_inventory_summary(
        selected_targets=targets,
        total_inventory_attempts=1,
        total_read_time=0.1,
        total_read_count=1,
        ant_read_counts={"ANT1": 1},
        ant_inventory_counts={"ANT1": 1},
        ant_skip_counts={"ANT1": 0},
        last_used_antenna_label="ANT1",
        restore_result={"requested": False, "target_label": None, "success": None, "message": "not_requested"},
        saved_at="2026-06-18T09:00:00",
    )
    path = tmp_path / "8ch_summary.json"

    _append_8ch_summary_to_json(str(path), summary)
    _append_8ch_summary_to_json(str(path), summary)

    history = json.loads(path.read_text(encoding="utf-8"))
    assert len(history) == 2
    assert history[0]["ant_results"][0]["antenna_label"] == "ANT1"
    assert "pc_uii" not in json.dumps(history, ensure_ascii=False).lower()
