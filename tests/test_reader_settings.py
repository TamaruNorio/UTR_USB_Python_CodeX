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
    assert parsed["parameter_kind"] == 0x01
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
    response = bytes.fromhex("02 00 30 04 43 02 00 05 03 83 0D")

    parsed = parse_frequency_setting_response(response)

    assert parsed["detail_command"] == 0x43
    assert parsed["parameter_kind"] == 0x02
    assert parsed["channel_number"] == 5
    assert parsed["frequency_mhz"] == 916.8
    assert parsed["raw_data_hex"] == "43 02 00 05"
    assert "送信周波数: 916.8 MHz" in format_frequency_setting(parsed)


def test_parse_frequency_setting_response_keeps_unknown_channel_as_raw_hex():
    response = bytes.fromhex("02 00 30 04 43 02 00 FF 03 7D 0D")

    parsed = parse_frequency_setting_response(response)

    assert parsed["channel_number"] == 0xFF
    assert parsed["frequency_mhz"] is None
    assert parsed["raw_data_hex"] == "43 02 00 FF"
    assert "既知範囲外" in "\n".join(format_frequency_setting(parsed))


def test_parse_output_power_setting_response_rejects_broken_sum():
    response = bytes.fromhex("02 00 30 05 43 01 00 F0 00 03 00 0D")

    with pytest.raises(ValueError, match="SUM"):
        parse_output_power_setting_response(response)
