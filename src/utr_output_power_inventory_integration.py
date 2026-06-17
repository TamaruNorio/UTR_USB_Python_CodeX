#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Inventory本体へ送信出力一時変更を組み込むための判定ヘルパー。

このモジュールは、既存Inventory処理へ送信出力一時変更UIを接続する前に、
「その機種・現在設定で一時変更を提案してよいか」を判定する純粋関数を提供します。

重要:
- USB実機通信は行いません。
- 送信出力変更コマンドは生成しません。
- 送信出力変更コマンドは送信しません。
- FLASH保存は行いません。
- Inventory動作は変更しません。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUPPORTED_OUTPUT_POWER_TEMPORARY_CHANGE_MODEL_KEYS = frozenset({"UTR-SUN02-4CH"})


@dataclass(frozen=True)
class OutputPowerTemporaryChangeAvailability:
    """送信出力一時変更UIを提示してよいかを表す判定結果。"""

    can_offer: bool
    reason: str


def evaluate_output_power_temporary_change_availability(
    identified_model_key: str | None,
    parsed_current_setting: dict[str, Any] | None,
) -> OutputPowerTemporaryChangeAvailability:
    """Inventory前に送信出力一時変更を提案してよいか判定します。

    Args:
        identified_model_key:
            ROMシリーズ名から照合した機種キー。
            現時点で許可するのは `UTR-SUN02-4CH` のみです。
        parsed_current_setting:
            `parse_output_power_setting_response()` の戻り値。
            復元に必要な現在値とキャリア関連時間が含まれている必要があります。

    Returns:
        OutputPowerTemporaryChangeAvailability:
            `can_offer=True` の場合だけ、UI側で一時変更を提案できます。
    """
    if identified_model_key not in SUPPORTED_OUTPUT_POWER_TEMPORARY_CHANGE_MODEL_KEYS:
        return OutputPowerTemporaryChangeAvailability(
            can_offer=False,
            reason="送信出力一時変更は、現時点ではUTR-SUN02-4CH / USM02のみ対象です。",
        )

    if parsed_current_setting is None:
        return OutputPowerTemporaryChangeAvailability(
            can_offer=False,
            reason="現在の送信出力設定を読み取れていないため、一時変更は提案しません。",
        )

    if parsed_current_setting.get("output_power_dbm") is None:
        return OutputPowerTemporaryChangeAvailability(
            can_offer=False,
            reason="現在の送信出力値を読み取れていないため、一時変更は提案しません。",
        )

    if parsed_current_setting.get("timing_settings") is None:
        return OutputPowerTemporaryChangeAvailability(
            can_offer=False,
            reason="復元に必要なキャリア関連時間を読み取れていないため、一時変更は提案しません。",
        )

    return OutputPowerTemporaryChangeAvailability(
        can_offer=True,
        reason="送信出力一時変更を提案できます。",
    )


def format_output_power_temporary_change_offer(availability: OutputPowerTemporaryChangeAvailability) -> list[str]:
    """Inventory前の画面表示に使う説明文を返します。"""
    if availability.can_offer:
        return [
            "送信出力の一時変更が可能です。",
            "FLASHは変更しません。",
            "Inventory終了時に元の送信出力へ戻します。",
        ]

    return [
        "送信出力の一時変更は行いません。",
        availability.reason,
    ]
