#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reader setting response helper tests."""

import pytest

from src.utr_reader_settings import (
    format_frequency_setting,
    format_output_power_setting,
    parse_frequency_setting_response,
    parse_output_power_setting_response,
)
from src.utr_output_power_readout import OutputPowerTimingSettings


def test_parse_output_power_setting_response_reads_dbm_and_raw_hex():
    response = bytes.fromhex("02 00 30 05 43 01 00 F0 00 03 6E 0D")

    parsed = parse_output_power_setting_response(response)

    assert parsed["detail_command"] == 0x43
    assert parsed["parameter_kind"] == 0x00
    assert parsed["output_power_dbm"] == 24.0
    assert parsed["raw_value_hex"] == "F0 00"
    assert parsed["raw_data_hex"] == "43 01 00 F0 00"
    assert parsed["timing_settings"] is None
    formatted = format_output_power_setting(parsed)
    assert "送信出力値: 24.0 dBm" in formatted
    assert "キャリア関連時間: レスポンスに含まれていないため表示しません" in formatted


def test_parse_output_power_setting_response_reads_timing_values_when_available():
    response = bytes.fromhex("02 00 30 0B 43 01 00 F0 00 D0 07 32 00 C8 00 03 45 0D")

    parsed = parse_output_power_setting_response(response)

    assert parsed["output_power_dbm"] == 24.0
    assert parsed["timing_settings"] == OutputPowerTimingSettings(
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )
    formatted = format_output_power_setting(parsed)
    assert "キャリア送信時間: 2000 msec" in formatted
    assert "キャリア休止時間: 50 msec" in formatted
    assert "キャリアセンス待ち時間: 200 msec" in formatted
    assert "送信出力Raw: 43 01 00 F0 00 D0 07 32 00 C8 00" in formatted


def test_parse_frequency_setting_response_reads_channel_and_frequency():
    response = bytes.fromhex("02 00 30 0C 43 02 00 1A 1A C0 1F 00 00 00 00 00 03 99 0D")

    parsed = parse_frequency_setting_response(response)

    assert parsed["detail_command"] == 0x43
    assert parsed["parameter_kind"] == 0x00
    assert parsed["starting_channel_number"] == 26
    assert parsed["current_channel_number"] == 26
    assert parsed["enabled_channels"] == (26, 27, 28, 29, 30, 31, 32)
    assert parsed["frequency_mhz"] == 921.0
    assert "現在チャンネル周波数: 921.0 MHz" in format_frequency_setting(parsed)


def test_parse_frequency_setting_response_rejects_short_legacy_shape():
    response = bytes.fromhex("02 00 30 04 43 02 00 05 03 83 0D")

    with pytest.raises(ValueError, match="短すぎ"):
        parse_frequency_setting_response(response)


def test_parse_output_power_setting_response_rejects_broken_sum():
    response = bytes.fromhex("02 00 30 05 43 01 00 F0 00 03 00 0D")

    with pytest.raises(ValueError, match="SUM"):
        parse_output_power_setting_response(response)
