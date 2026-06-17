#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reader setting response helpers for UTR UHF read-only commands."""

from __future__ import annotations

from typing import Any

try:
    from src.utr_output_power_readout import (
        format_output_power_timing_settings,
        parse_output_power_timing_settings_from_data,
    )
    from src.utr_protocol import ACK, CR, ETX, STX, CMD_LOCATION, calculate_sum_value, parse_output_power_dbm
except ModuleNotFoundError:
    from utr_output_power_readout import (
        format_output_power_timing_settings,
        parse_output_power_timing_settings_from_data,
    )
    from utr_protocol import ACK, CR, ETX, STX, CMD_LOCATION, calculate_sum_value, parse_output_power_dbm


DETAIL_READER_SETTING_READ = 0x43
PARAMETER_KIND_OUTPUT_POWER = 0x01
PARAMETER_KIND_FREQUENCY_CHANNEL = 0x02

OUTPUT_CH_FREQ_LIST = [
    916.0, 916.2, 916.4, 916.6, 916.8, 917.0, 917.2, 917.4,
    917.6, 917.8, 918.0, 918.2, 918.4, 918.6, 918.8, 919.0,
    919.2, 919.4, 919.6, 919.8, 920.0, 920.2, 920.4, 920.6,
    920.8, 921.0, 921.2, 921.4, 921.6, 921.8, 922.0, 922.2,
    922.4, 922.6, 922.8, 923.0, 923.2, 923.4,
]


def _validate_reader_setting_ack(frame: bytes, parameter_kind: int, min_data_length: int) -> bytes:
    if len(frame) < 7:
        raise ValueError("レスポンス長が短すぎます。")
    if frame[0:1] != STX or frame[-1:] != CR:
        raise ValueError("STXまたはCRが一致しません。")
    if frame[CMD_LOCATION:CMD_LOCATION + 1] != ACK:
        raise ValueError("ACKレスポンスではありません。")

    data_length = frame[3]
    expected_frame_length = 4 + data_length + 3
    if len(frame) != expected_frame_length:
        raise ValueError("データ長とフレーム長が一致しません。")

    etx_index = 4 + data_length
    if frame[etx_index:etx_index + 1] != ETX:
        raise ValueError("ETX位置が一致しません。")
    if calculate_sum_value(frame[:-2]) != frame[-2]:
        raise ValueError("SUMが一致しません。")

    data = frame[4:4 + data_length]
    if len(data) < min_data_length:
        raise ValueError("データ部が短すぎます。")
    if data[0] != DETAIL_READER_SETTING_READ:
        raise ValueError(f"詳細コマンドが一致しません: 0x{data[0]:02X}")
    if data[1] != parameter_kind:
        raise ValueError(f"パラメータ種別が一致しません: 0x{data[1]:02X}")
    return data


def parse_output_power_setting_response(frame: bytes) -> dict[str, Any]:
    """Parse UHF_READ_OUTPUT_POWER response into display-friendly values."""
    data = _validate_reader_setting_ack(
        frame,
        parameter_kind=PARAMETER_KIND_OUTPUT_POWER,
        min_data_length=5,
    )
    output_power_bytes = data[3:5]
    timing_settings = parse_output_power_timing_settings_from_data(data)
    return {
        "detail_command": data[0],
        "parameter_kind": data[1],
        "raw_data_hex": data.hex(" ").upper(),
        "raw_value_hex": output_power_bytes.hex(" ").upper(),
        "output_power_dbm": parse_output_power_dbm(output_power_bytes),
        "timing_settings": timing_settings,
    }


def parse_frequency_setting_response(frame: bytes) -> dict[str, Any]:
    """Parse UHF_READ_FREQ_CH response into display-friendly values."""
    data = _validate_reader_setting_ack(
        frame,
        parameter_kind=PARAMETER_KIND_FREQUENCY_CHANNEL,
        min_data_length=4,
    )
    channel_number = data[3]
    frequency_mhz = None
    if 1 <= channel_number <= len(OUTPUT_CH_FREQ_LIST):
        frequency_mhz = OUTPUT_CH_FREQ_LIST[channel_number - 1]

    return {
        "detail_command": data[0],
        "parameter_kind": data[1],
        "raw_data_hex": data.hex(" ").upper(),
        "channel_number": channel_number,
        "frequency_mhz": frequency_mhz,
    }


def format_output_power_setting(parsed: dict[str, Any]) -> list[str]:
    """Format parsed output power setting for display."""
    return [
        f"送信出力値: {parsed['output_power_dbm']} dBm",
        *format_output_power_timing_settings(parsed.get("timing_settings")),
        f"送信出力Raw: {parsed['raw_data_hex']}",
    ]


def format_frequency_setting(parsed: dict[str, Any]) -> list[str]:
    """Format parsed frequency setting for display."""
    lines = [
        f"チャンネル番号: {parsed['channel_number']} ch",
    ]
    if parsed["frequency_mhz"] is not None:
        lines.append(f"送信周波数: {parsed['frequency_mhz']} MHz")
    else:
        lines.append("送信周波数: チャンネル番号が既知範囲外のため換算できません")
    lines.append(f"周波数設定Raw: {parsed['raw_data_hex']}")
    return lines
