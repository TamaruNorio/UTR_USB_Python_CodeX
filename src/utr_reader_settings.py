#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reader setting response helpers for UTR UHF read-only commands."""

from __future__ import annotations

from dataclasses import dataclass
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

VALID_FREQUENCY_CHANNELS = (5, 11, 17, *range(23, 38))


@dataclass(frozen=True)
class FrequencySetting:
    parameter_kind: int
    starting_channel: int
    current_channel: int
    enabled_channels: tuple[int, ...]
    channel_mask: bytes
    reserved: bytes
    raw: bytes


def channel_to_frequency_mhz(channel_number: int) -> float | None:
    if 1 <= channel_number <= len(OUTPUT_CH_FREQ_LIST):
        return OUTPUT_CH_FREQ_LIST[channel_number - 1]
    return None


def _decode_frequency_channel_mask(mask: bytes) -> tuple[int, ...]:
    if len(mask) != 3:
        raise ValueError("frequency channel mask must be exactly 3 bytes")
    if mask[2] & 0xFC:
        raise ValueError("frequency channel mask reserved bits must be zero")
    return tuple(
        channel
        for index, channel in enumerate(VALID_FREQUENCY_CHANNELS)
        if mask[index // 8] & (1 << (index % 8))
    )


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
        "parameter_kind": data[2],
        "raw_data_hex": data.hex(" ").upper(),
        "raw_value_hex": output_power_bytes.hex(" ").upper(),
        "output_power_dbm": parse_output_power_dbm(output_power_bytes),
        "timing_settings": timing_settings,
    }


def parse_frequency_setting_response(frame: bytes) -> dict[str, Any]:
    """7.4.7の12バイトACKを開始CH・現在CH・使用CHへ分解します。"""
    data = _validate_reader_setting_ack(
        frame,
        parameter_kind=PARAMETER_KIND_FREQUENCY_CHANNEL,
        min_data_length=12,
    )
    if len(data) != 12:
        raise ValueError("周波数設定レスポンスのDATA長は12バイトである必要があります。")
    setting = FrequencySetting(
        parameter_kind=data[2],
        starting_channel=data[3],
        current_channel=data[4],
        enabled_channels=_decode_frequency_channel_mask(data[5:8]),
        channel_mask=data[5:8],
        reserved=data[8:12],
        raw=data,
    )
    if setting.starting_channel not in VALID_FREQUENCY_CHANNELS:
        raise ValueError("周波数の開始チャンネル番号が仕様範囲外です。")
    if setting.starting_channel not in setting.enabled_channels:
        raise ValueError("周波数の開始チャンネルが使用許可されていません。")
    if setting.current_channel not in VALID_FREQUENCY_CHANNELS:
        raise ValueError("現在設定されているチャンネル番号が仕様範囲外です。")

    return {
        "detail_command": data[0],
        "parameter_kind": data[2],
        "raw_data_hex": data.hex(" ").upper(),
        # 後方互換キー。現在設定CHを表します。
        "channel_number": setting.current_channel,
        "frequency_mhz": channel_to_frequency_mhz(setting.current_channel),
        "starting_channel_number": setting.starting_channel,
        "starting_frequency_mhz": channel_to_frequency_mhz(setting.starting_channel),
        "current_channel_number": setting.current_channel,
        "current_frequency_mhz": channel_to_frequency_mhz(setting.current_channel),
        "enabled_channels": setting.enabled_channels,
        "channel_mask": setting.channel_mask,
        "reserved": setting.reserved,
        "setting": setting,
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
        f"開始チャンネル番号: {parsed['starting_channel_number']} ch",
        f"現在チャンネル番号: {parsed['current_channel_number']} ch",
        f"使用チャンネル: {list(parsed['enabled_channels'])}",
    ]
    if parsed["current_frequency_mhz"] is not None:
        lines.append(f"現在チャンネル周波数: {parsed['current_frequency_mhz']} MHz")
    else:
        lines.append("現在チャンネル周波数: チャンネル番号が既知範囲外のため換算できません")
    lines.append(f"周波数設定Raw: {parsed['raw_data_hex']}")
    return lines
