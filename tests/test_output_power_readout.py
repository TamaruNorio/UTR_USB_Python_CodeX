#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力設定読み取り結果の補助パーサのテスト。"""

import pytest

from src.utr_output_power_readout import (
    OutputPowerTimingSettings,
    format_output_power_timing_settings,
    parse_output_power_timing_settings_from_data,
)


def test_parse_output_power_timing_settings_from_full_data():
    data = bytes.fromhex("43 01 00 F0 00 D0 07 32 00 C8 00")

    timing = parse_output_power_timing_settings_from_data(data)

    assert timing == OutputPowerTimingSettings(
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )


def test_parse_output_power_timing_settings_returns_none_for_short_data():
    data = bytes.fromhex("43 01 00 F0 00")

    assert parse_output_power_timing_settings_from_data(data) is None


def test_parse_output_power_timing_settings_rejects_unexpected_long_data():
    data = bytes.fromhex("43 01 00 F0 00 D0 07 32 00 C8 00 00")

    with pytest.raises(ValueError, match="unexpected output setting data length"):
        parse_output_power_timing_settings_from_data(data)


def test_format_output_power_timing_settings_for_values():
    lines = format_output_power_timing_settings(
        OutputPowerTimingSettings(
            carrier_transmission_time_ms=2000,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        )
    )

    assert lines == [
        "キャリア送信時間: 2000 msec",
        "キャリア休止時間: 50 msec",
        "キャリアセンス待ち時間: 200 msec",
    ]


def test_format_output_power_timing_settings_for_missing_values():
    lines = format_output_power_timing_settings(None)

    assert lines == ["キャリア関連時間: レスポンスに含まれていないため表示しません"]
