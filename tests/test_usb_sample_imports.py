#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""src.utr_usb_sample のimport漏れ防止テスト。"""

from src import utr_usb_sample
from src.utr_antenna import AntennaCheckTarget


def test_utr_usb_sample_imports_format_antenna_numbers():
    assert callable(utr_usb_sample.format_antenna_numbers)
    assert utr_usb_sample.format_antenna_numbers([0, 1]) == "Ant0, Ant1"

def _antenna_targets():
    return [
        AntennaCheckTarget(0, "ANT0", "内蔵アンテナ"),
        AntennaCheckTarget(1, "ANT1", "外付けアンテナ1"),
    ]


def test_parse_inventory_antenna_selection_input_supports_comma_separated_values():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "0,1")
    assert [target.number for target in selected] == [0, 1]


def test_parse_inventory_antenna_selection_input_supports_all():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "all")
    assert [target.number for target in selected] == [0, 1]


def test_parse_inventory_antenna_selection_input_removes_duplicates_but_keeps_order():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "1,1,0")
    assert [target.number for target in selected] == [1, 0]


def test_parse_inventory_antenna_selection_input_q_returns_none():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "q")
    assert selected is None
