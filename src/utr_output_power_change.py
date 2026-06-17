#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力一時変更の計画ヘルパー。

このモジュールは、将来のUI接続に備えて
「入力値を解釈し、送信候補フレームと表示用情報を作る」ところまでを扱います。

重要:
- USB実機通信は行いません。
- 生成したフレームを送信しません。
- FLASH保存は行いません。
- Inventory動作は変更しません。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

try:
    from src.utr_commands import (
        PARAMETER_KIND_COMMAND_MODE,
        build_write_output_setting_command,
    )
    from src.utr_output_power import parse_output_power_dbm_input
except ModuleNotFoundError:
    from utr_commands import (
        PARAMETER_KIND_COMMAND_MODE,
        build_write_output_setting_command,
    )
    from utr_output_power import parse_output_power_dbm_input


@dataclass(frozen=True)
class OutputPowerChangePlan:
    """送信出力一時変更の確認用データ。

    このクラスは確認画面やテストで使うための入れ物です。
    実機へコマンドを送信する責務は持ちません。
    """

    parameter_kind: int
    target_output_power_dbm: Decimal
    carrier_transmission_time_ms: int
    carrier_off_time_ms: int
    carrier_sense_wait_time_ms: int
    command_frame: bytes

    @property
    def command_frame_hex(self) -> str:
        """送信候補フレームを人が確認しやすいHEX文字列で返します。"""
        return self.command_frame.hex(" ").upper()


def build_output_power_change_plan(
    user_input: str,
    *,
    carrier_transmission_time_ms: int,
    carrier_off_time_ms: int,
    carrier_sense_wait_time_ms: int,
    parameter_kind: int = PARAMETER_KIND_COMMAND_MODE,
) -> OutputPowerChangePlan | None:
    """送信出力一時変更の候補計画を作成します。

    Args:
        user_input:
            ユーザーが入力した送信出力値。
            空文字、q、quit、cancel は変更中止として扱います。
        carrier_transmission_time_ms:
            現在設定から引き継ぐキャリア送信時間[msec]。
        carrier_off_time_ms:
            現在設定から引き継ぐキャリア休止時間[msec]。
        carrier_sense_wait_time_ms:
            現在設定から引き継ぐキャリアセンス待ち時間[msec]。
        parameter_kind:
            書き込み先パラメータ種類。
            初期利用想定はコマンドモード用パラメータです。

    Returns:
        変更中止の場合は None。
        変更候補が有効な場合は OutputPowerChangePlan。

    Raises:
        ValueError: 入力値、parameter_kind、各時間値が不正な場合。
    """
    target_output_power_dbm = parse_output_power_dbm_input(user_input)
    if target_output_power_dbm is None:
        return None

    command_frame = build_write_output_setting_command(
        parameter_kind=parameter_kind,
        output_power_dbm=target_output_power_dbm,
        carrier_transmission_time_ms=carrier_transmission_time_ms,
        carrier_off_time_ms=carrier_off_time_ms,
        carrier_sense_wait_time_ms=carrier_sense_wait_time_ms,
    )

    return OutputPowerChangePlan(
        parameter_kind=parameter_kind,
        target_output_power_dbm=target_output_power_dbm,
        carrier_transmission_time_ms=carrier_transmission_time_ms,
        carrier_off_time_ms=carrier_off_time_ms,
        carrier_sense_wait_time_ms=carrier_sense_wait_time_ms,
        command_frame=command_frame,
    )


def format_output_power_change_plan(plan: OutputPowerChangePlan) -> list[str]:
    """送信出力一時変更の確認表示用テキストを作成します。"""
    return [
        "=== 送信出力一時変更の確認 ===",
        f"書き込み先パラメータ種別: 0x{plan.parameter_kind:02X}",
        f"変更後の送信出力: {plan.target_output_power_dbm} dBm",
        f"キャリア送信時間: {plan.carrier_transmission_time_ms} msec",
        f"キャリア休止時間: {plan.carrier_off_time_ms} msec",
        f"キャリアセンス待ち時間: {plan.carrier_sense_wait_time_ms} msec",
        "FLASHは変更しません。",
        f"送信候補フレーム: {plan.command_frame_hex}",
    ]
