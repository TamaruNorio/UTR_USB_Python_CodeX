#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力一時変更と復元の計画ヘルパー。

このモジュールは、既存の読み取り結果をもとに、
将来UIから一時変更を実行するための「変更計画」と「復元計画」を作ります。

重要:
- USB実機通信は行いません。
- 生成したフレームを送信しません。
- FLASH保存は行いません。
- Inventory動作は変更しません。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from src.utr_commands import PARAMETER_KIND_COMMAND_MODE
    from src.utr_output_power_change import OutputPowerChangePlan, build_output_power_change_plan
except ModuleNotFoundError:
    from utr_commands import PARAMETER_KIND_COMMAND_MODE
    from utr_output_power_change import OutputPowerChangePlan, build_output_power_change_plan


@dataclass(frozen=True)
class OutputPowerTemporaryChangePlans:
    """送信出力一時変更と復元に必要な2つの計画。"""

    change_plan: OutputPowerChangePlan
    restore_plan: OutputPowerChangePlan


def build_output_power_temporary_change_plans(
    parsed_current_setting: dict[str, Any],
    user_input: str,
    *,
    parameter_kind: int = PARAMETER_KIND_COMMAND_MODE,
) -> OutputPowerTemporaryChangePlans | None:
    """現在設定から、送信出力一時変更計画と復元計画を作成します。

    Args:
        parsed_current_setting:
            `parse_output_power_setting_response()` の戻り値。
            `output_power_dbm` と `timing_settings` を使用します。
        user_input:
            ユーザーが入力した変更後の送信出力値。
            空文字、q、quit、cancel は変更中止として扱います。
        parameter_kind:
            書き込み先パラメータ種類。
            初期利用想定はコマンドモード用パラメータです。

    Returns:
        変更中止の場合は None。
        有効な入力の場合は、変更計画と復元計画を返します。

    Raises:
        ValueError:
            現在設定に復元に必要な情報がない場合、または入力値が不正な場合。
    """
    timing_settings = parsed_current_setting.get("timing_settings")
    if timing_settings is None:
        raise ValueError("送信出力の復元に必要なキャリア関連時間が読み取れていません。")

    current_output_power_dbm = parsed_current_setting.get("output_power_dbm")
    if current_output_power_dbm is None:
        raise ValueError("送信出力の復元に必要な現在の送信出力値が読み取れていません。")

    change_plan = build_output_power_change_plan(
        user_input,
        parameter_kind=parameter_kind,
        carrier_transmission_time_ms=timing_settings.carrier_transmission_time_ms,
        carrier_off_time_ms=timing_settings.carrier_off_time_ms,
        carrier_sense_wait_time_ms=timing_settings.carrier_sense_wait_time_ms,
    )
    if change_plan is None:
        return None

    restore_plan = build_output_power_change_plan(
        str(current_output_power_dbm),
        parameter_kind=parameter_kind,
        carrier_transmission_time_ms=timing_settings.carrier_transmission_time_ms,
        carrier_off_time_ms=timing_settings.carrier_off_time_ms,
        carrier_sense_wait_time_ms=timing_settings.carrier_sense_wait_time_ms,
    )
    if restore_plan is None:
        # 現在値から復元計画が作れない場合は、変更へ進ませない。
        raise ValueError("送信出力の復元計画を作成できません。")

    return OutputPowerTemporaryChangePlans(
        change_plan=change_plan,
        restore_plan=restore_plan,
    )


def format_output_power_temporary_change_plans(plans: OutputPowerTemporaryChangePlans) -> list[str]:
    """変更前確認に使う表示用テキストを作成します。"""
    return [
        "=== 送信出力一時変更の最終確認 ===",
        f"現在の送信出力: {plans.restore_plan.target_output_power_dbm} dBm",
        f"変更後の送信出力: {plans.change_plan.target_output_power_dbm} dBm",
        "FLASHは変更しません。",
        "終了時に元の送信出力へ戻します。",
        f"変更用フレーム: {plans.change_plan.command_frame_hex}",
        f"復元用フレーム: {plans.restore_plan.command_frame_hex}",
    ]
