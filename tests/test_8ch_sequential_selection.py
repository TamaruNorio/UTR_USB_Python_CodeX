#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""8CH順次Inventory向けの選択順テスト。"""

from src.utr_8ch import build_8ch_inventory_targets, parse_8ch_inventory_selection_input
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
