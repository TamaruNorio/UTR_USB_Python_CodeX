#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""8CH順次Inventory向けの選択順テスト。"""

from src.utr_8ch import build_8ch_inventory_targets, parse_8ch_inventory_selection_input
from src.utr_8ch_sequential_inventory_cli import _parse_restore_usage_antenna_target_input
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
