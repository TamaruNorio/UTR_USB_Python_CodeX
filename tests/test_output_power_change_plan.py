#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力一時変更計画ヘルパーのテスト。"""

from decimal import Decimal

import pytest

from src.utr_commands import PARAMETER_KIND_COMMAND_MODE, PARAMETER_KIND_FLASH
from src.utr_output_power_change import (
    OutputPowerChangePlan,
    build_output_power_change_plan,
    format_output_power_change_plan,
)


def test_build_output_power_change_plan_returns_none_for_cancel_input():
    plan = build_output_power_change_plan(
        "q",
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )

    assert plan is None


def test_build_output_power_change_plan_builds_plan_with_command_frame():
    plan = build_output_power_change_plan(
        "24.0",
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )

    assert isinstance(plan, OutputPowerChangePlan)
    assert plan.parameter_kind == PARAMETER_KIND_COMMAND_MODE
    assert plan.target_output_power_dbm == Decimal("24.0")
    assert plan.carrier_transmission_time_ms == 2000
    assert plan.carrier_off_time_ms == 50
    assert plan.carrier_sense_wait_time_ms == 200
    assert plan.command_frame == bytes.fromhex("02 00 55 0B 33 01 00 F0 00 D0 07 32 00 C8 00 03 5A 0D")
    assert plan.command_frame_hex == "02 00 55 0B 33 01 00 F0 00 D0 07 32 00 C8 00 03 5A 0D"


def test_build_output_power_change_plan_rejects_flash_target():
    with pytest.raises(ValueError, match="FLASH"):
        build_output_power_change_plan(
            "24.0",
            parameter_kind=PARAMETER_KIND_FLASH,
            carrier_transmission_time_ms=2000,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        )


def test_build_output_power_change_plan_rejects_invalid_input_value():
    with pytest.raises(ValueError):
        build_output_power_change_plan(
            "24.05",
            carrier_transmission_time_ms=2000,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        )


def test_format_output_power_change_plan_contains_safety_message_and_frame():
    plan = build_output_power_change_plan(
        "24.0",
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )

    assert plan is not None
    lines = format_output_power_change_plan(plan)

    assert "FLASHは変更しません。" in lines
    assert "変更後の送信出力: 24.0 dBm" in lines
    assert "送信候補フレーム: 02 00 55 0B 33 01 00 F0 00 D0 07 32 00 C8 00 03 5A 0D" in lines
