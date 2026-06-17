#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力一時変更・復元計画ヘルパーのテスト。"""

from decimal import Decimal

import pytest

from src.utr_output_power_readout import OutputPowerTimingSettings
from src.utr_output_power_temporary_change import (
    OutputPowerTemporaryChangePlans,
    build_output_power_temporary_change_plans,
    format_output_power_temporary_change_plans,
)


def _current_setting() -> dict:
    return {
        "output_power_dbm": 24.0,
        "timing_settings": OutputPowerTimingSettings(
            carrier_transmission_time_ms=100,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        ),
    }


def test_build_output_power_temporary_change_plans_returns_none_for_cancel_input():
    plans = build_output_power_temporary_change_plans(_current_setting(), "q")

    assert plans is None


def test_build_output_power_temporary_change_plans_builds_change_and_restore_plans():
    plans = build_output_power_temporary_change_plans(_current_setting(), "20.0")

    assert isinstance(plans, OutputPowerTemporaryChangePlans)
    assert plans.change_plan.target_output_power_dbm == Decimal("20.0")
    assert plans.restore_plan.target_output_power_dbm == Decimal("24.0")
    assert plans.change_plan.command_frame == bytes.fromhex("02 00 55 0B 33 01 00 C8 00 64 00 32 00 C8 00 03 BF 0D")
    assert plans.restore_plan.command_frame == bytes.fromhex("02 00 55 0B 33 01 00 F0 00 64 00 32 00 C8 00 03 E7 0D")


def test_build_output_power_temporary_change_plans_rejects_missing_timing_settings():
    current_setting = {"output_power_dbm": 24.0, "timing_settings": None}

    with pytest.raises(ValueError, match="キャリア関連時間"):
        build_output_power_temporary_change_plans(current_setting, "20.0")


def test_build_output_power_temporary_change_plans_rejects_missing_current_output_power():
    current_setting = {"timing_settings": _current_setting()["timing_settings"]}

    with pytest.raises(ValueError, match="現在の送信出力値"):
        build_output_power_temporary_change_plans(current_setting, "20.0")


def test_format_output_power_temporary_change_plans_contains_safety_lines():
    plans = build_output_power_temporary_change_plans(_current_setting(), "20.0")

    assert plans is not None
    lines = format_output_power_temporary_change_plans(plans)

    assert "現在の送信出力: 24.0 dBm" in lines
    assert "変更後の送信出力: 20.0 dBm" in lines
    assert "FLASHは変更しません。" in lines
    assert "終了時に元の送信出力へ戻します。" in lines
