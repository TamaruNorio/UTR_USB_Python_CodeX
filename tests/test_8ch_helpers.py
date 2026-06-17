#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向け補助関数のテスト。"""

import pytest

from src.utr_8ch import (
    build_8ch_inventory_target,
    build_8ch_inventory_targets,
    check_antenna_number_to_physical_port,
    format_8ch_diagnostic_notes,
    format_8ch_inventory_candidate,
    is_8ch_model_key,
    parse_8ch_inventory_selection_input,
    physical_port_to_sun02_8ch_usage_antenna_number,
)
from src.utr_antenna import AntennaCheckTarget


def test_is_8ch_model_key_accepts_8ch_models():
    assert is_8ch_model_key("UTR-SUN02V-8CH") is True
    assert is_8ch_model_key("UTR-SUN02-8CH") is True


def test_is_8ch_model_key_rejects_non_8ch_models():
    assert is_8ch_model_key("UTR-SUN02-4CH") is False
    assert is_8ch_model_key("UTR-S201") is False
    assert is_8ch_model_key(None) is False


def test_format_8ch_diagnostic_notes_for_sun02_8ch():
    lines = format_8ch_diagnostic_notes("UTR-SUN02-8CH")

    assert any("UTR-SUN02-8CH" in line for line in lines)
    assert any("00h〜07h" in line for line in lines)
    assert any("ANT8=E0h" in line for line in lines)
    assert any("FLASHは変更しません" in line for line in lines)


def test_format_8ch_diagnostic_notes_for_sun02v_8ch():
    lines = format_8ch_diagnostic_notes("UTR-SUN02V-8CH")

    assert any("UTR-SUN02V-8CH" in line for line in lines)
    assert any("00h〜07h" in line for line in lines)
    assert any("内部アンテナ番号×32" in line for line in lines)
    assert any("FLASHは変更しません" in line for line in lines)


def test_format_8ch_diagnostic_notes_for_non_8ch_model():
    assert format_8ch_diagnostic_notes("UTR-SUN02-4CH") == [
        "8CH機ではないため、8CH専用診断は実行しません。",
    ]


def test_check_antenna_number_to_physical_port():
    assert check_antenna_number_to_physical_port(0x00) == 1
    assert check_antenna_number_to_physical_port(0x07) == 8

    with pytest.raises(ValueError, match="range 0-7"):
        check_antenna_number_to_physical_port(0x08)


def test_physical_port_to_sun02_8ch_usage_antenna_number():
    assert physical_port_to_sun02_8ch_usage_antenna_number(1) == 0x00
    assert physical_port_to_sun02_8ch_usage_antenna_number(2) == 0x20
    assert physical_port_to_sun02_8ch_usage_antenna_number(8) == 0xE0

    with pytest.raises(ValueError, match="range 1-8"):
        physical_port_to_sun02_8ch_usage_antenna_number(0)


def test_build_8ch_inventory_target():
    check_target = AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ")

    target = build_8ch_inventory_target(check_target)

    assert target.check_target == check_target
    assert target.physical_port == 1
    assert target.usage_antenna_number == 0x00
    assert target.label == "ANT1"
    assert target.usage_antenna_number_hex == "00h"


def test_build_8ch_inventory_targets():
    check_targets = [
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x07, "ANT8", "外付けアンテナ"),
    ]

    targets = build_8ch_inventory_targets(check_targets)

    assert [target.physical_port for target in targets] == [1, 8]
    assert [target.usage_antenna_number for target in targets] == [0x00, 0xE0]


def test_format_8ch_inventory_candidate():
    target = build_8ch_inventory_target(AntennaCheckTarget(0x07, "ANT8", "外付けアンテナ"))

    assert format_8ch_inventory_candidate(target) == "[8] ANT8（使用アンテナ番号: E0h）"


def test_parse_8ch_inventory_selection_input_supports_all_and_numbers():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
        AntennaCheckTarget(0x03, "ANT4", "外付けアンテナ"),
    ])

    assert parse_8ch_inventory_selection_input(targets, "all") == targets
    assert parse_8ch_inventory_selection_input(targets, "1") == [targets[0]]
    assert parse_8ch_inventory_selection_input(targets, "1,4") == targets
    assert parse_8ch_inventory_selection_input(targets, "1,1,4") == targets


def test_parse_8ch_inventory_selection_input_supports_cancel():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
    ])

    assert parse_8ch_inventory_selection_input(targets, "q") is None
    assert parse_8ch_inventory_selection_input(targets, "cancel") is None


def test_parse_8ch_inventory_selection_input_rejects_invalid_value():
    targets = build_8ch_inventory_targets([
        AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"),
    ])

    with pytest.raises(ValueError, match="候補に表示されているANT番号"):
        parse_8ch_inventory_selection_input(targets, "2")

    with pytest.raises(ValueError, match="数値"):
        parse_8ch_inventory_selection_input(targets, "ANT1")
