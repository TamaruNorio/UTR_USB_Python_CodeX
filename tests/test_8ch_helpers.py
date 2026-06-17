#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向け補助関数のテスト。"""

import pytest

from src.utr_8ch import (
    build_8ch_inventory_target,
    build_8ch_inventory_targets,
    build_sun02_8ch_usage_antenna_command_dry_run,
    check_antenna_number_to_physical_port,
    format_8ch_diagnostic_notes,
    format_8ch_inventory_candidate,
    format_8ch_usage_antenna_command_dry_run,
    is_8ch_model_key,
    parse_8ch_inventory_selection_input,
    physical_port_to_sun02_8ch_internal_antenna_number,
    physical_port_to_sun02_8ch_usage_antenna_number,
)
from src.utr_antenna import AntennaCheckTarget
from src.utr_protocol import calculate_sum_value


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


def test_physical_port_to_sun02_8ch_internal_antenna_number():
    assert physical_port_to_sun02_8ch_internal_antenna_number(1) == 0x00
    assert physical_port_to_sun02_8ch_internal_antenna_number(3) == 0x02
    assert physical_port_to_sun02_8ch_internal_antenna_number(8) == 0x07

    with pytest.raises(ValueError, match="range 1-8"):
        physical_port_to_sun02_8ch_internal_antenna_number(9)


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


def test_build_sun02_8ch_usage_antenna_command_dry_run_frames():
    ant1 = build_8ch_inventory_target(AntennaCheckTarget(0x00, "ANT1", "外付けアンテナ"))
    ant3 = build_8ch_inventory_target(AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"))
    ant8 = build_8ch_inventory_target(AntennaCheckTarget(0x07, "ANT8", "外付けアンテナ"))

    ant1_dry_run = build_sun02_8ch_usage_antenna_command_dry_run(ant1)
    ant3_dry_run = build_sun02_8ch_usage_antenna_command_dry_run(ant3)
    ant8_dry_run = build_sun02_8ch_usage_antenna_command_dry_run(ant8)

    assert ant1_dry_run.internal_antenna_number == 0x00
    assert ant1_dry_run.external_antenna_number == 0x00
    assert ant1_dry_run.frame == bytes.fromhex("020055043800000003960D")

    assert ant3_dry_run.internal_antenna_number == 0x02
    assert ant3_dry_run.external_antenna_number == 0x00
    assert ant3_dry_run.frame == bytes.fromhex("020055043800020003980D")

    assert ant8_dry_run.internal_antenna_number == 0x07
    assert ant8_dry_run.external_antenna_number == 0x00
    assert ant8_dry_run.frame == bytes.fromhex("0200550438000700039D0D")

    for dry_run in [ant1_dry_run, ant3_dry_run, ant8_dry_run]:
        assert dry_run.frame[0] == 0x02
        assert dry_run.frame[2] == 0x55
        assert dry_run.frame[3] == 0x04
        assert dry_run.frame[4] == 0x38
        assert dry_run.frame[-3] == 0x03
        assert dry_run.frame[-2] == calculate_sum_value(dry_run.frame[:-2])
        assert dry_run.frame[-1] == 0x0D


def test_format_8ch_usage_antenna_command_dry_run():
    target = build_8ch_inventory_target(AntennaCheckTarget(0x02, "ANT3", "外付けアンテナ"))
    dry_run = build_sun02_8ch_usage_antenna_command_dry_run(target)

    lines = format_8ch_usage_antenna_command_dry_run(dry_run)

    assert "対象アンテナ: ANT3" in lines
    assert "使用アンテナ番号: 40h" in lines
    assert "内部アンテナ番号: 02h" in lines
    assert "外部アンテナ番号: 00h" in lines
    assert "dry-run送信フレーム: 02 00 55 04 38 00 02 00 03 98 0D" in lines
    assert any("実機へは送信しません" in line for line in lines)


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
