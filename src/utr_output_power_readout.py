#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力設定読み取り結果の補助パーサ。

このモジュールは、将来の送信出力一時変更に備えて、
読み取り結果からキャリア関連時間を取り出すための純粋関数だけを扱います。

重要:
- USB実機通信は行いません。
- 送信出力の書き込みは行いません。
- FLASH保存は行いません。
- 既存のInventory動作は変更しません。
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from src.utr_protocol import parse_little_endian_u16
except ModuleNotFoundError:
    from utr_protocol import parse_little_endian_u16


FULL_OUTPUT_SETTING_DATA_LENGTH = 11


@dataclass(frozen=True)
class OutputPowerTimingSettings:
    """出力設定に含まれるキャリア関連時間。"""

    carrier_transmission_time_ms: int
    carrier_off_time_ms: int
    carrier_sense_wait_time_ms: int


def parse_output_power_timing_settings_from_data(data: bytes) -> OutputPowerTimingSettings | None:
    """出力設定データ部からキャリア関連時間を読み取ります。

    Args:
        data:
            UHF_READ_OUTPUT_POWER応答のデータ部。
            想定する完全形式は以下です。
            `43h, 01h, parameter_kind, output_power_LSB, output_power_MSB,
            carrier_tx_LSB, carrier_tx_MSB, carrier_off_LSB, carrier_off_MSB,
            carrier_sense_LSB, carrier_sense_MSB`

    Returns:
        データ部が完全形式なら OutputPowerTimingSettings。
        短い旧形式または情報不足の場合は None。

    Raises:
        ValueError: 完全形式を超える長さだが、想定外の長さの場合。
    """
    if len(data) < FULL_OUTPUT_SETTING_DATA_LENGTH:
        return None
    if len(data) != FULL_OUTPUT_SETTING_DATA_LENGTH:
        raise ValueError("unexpected output setting data length")

    return OutputPowerTimingSettings(
        carrier_transmission_time_ms=parse_little_endian_u16(data[5:7]),
        carrier_off_time_ms=parse_little_endian_u16(data[7:9]),
        carrier_sense_wait_time_ms=parse_little_endian_u16(data[9:11]),
    )


def format_output_power_timing_settings(timing: OutputPowerTimingSettings | None) -> list[str]:
    """キャリア関連時間を表示用テキストへ変換します。"""
    if timing is None:
        return ["キャリア関連時間: レスポンスに含まれていないため表示しません"]

    return [
        f"キャリア送信時間: {timing.carrier_transmission_time_ms} msec",
        f"キャリア休止時間: {timing.carrier_off_time_ms} msec",
        f"キャリアセンス待ち時間: {timing.carrier_sense_wait_time_ms} msec",
    ]
