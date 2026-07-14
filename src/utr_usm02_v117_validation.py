#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02向けVer.1.17検証計画を54件漏れなく生成する。"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

from src.utr_v117_catalog import COMMAND_SPECS, CommandSpec, PlanStatus, classify_for_usm02


@dataclass(frozen=True)
class ValidationPlanEntry:
    section: str
    name: str
    command_hex: str
    detail_hex: str | None
    subcommand_hex: str | None
    response_pattern: str
    ack_data_length: str
    operation: str
    plan_status: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _hex(value: int | None) -> str | None:
    return None if value is None else f"{value:02X}h"


def _reason(spec: CommandSpec, status: PlanStatus) -> str:
    if status == PlanStatus.READY:
        return "対象機種・ROM・ユーザー条件を満たせば検証可能"
    if status == PlanStatus.ROM_CHECK_REQUIRED:
        return f"実機ROM確認が必要（Ver.{spec.minimum_rom // 1000}.{spec.minimum_rom % 1000:03d}以降）"
    if status == PlanStatus.NOT_SUPPORTED_BY_DEVICE:
        return "USM02（4CH）では対象外のコマンド"
    if status == PlanStatus.NOT_SUPPORTED_BY_ROM:
        return f"実機ROMが必要版未満（必要={spec.minimum_rom}）"
    if status == PlanStatus.NOT_EXECUTED_BY_USER_DECISION:
        return spec.hold_reason or "ユーザー判断により実行しない"
    if status == PlanStatus.CONDITION_NOT_AVAILABLE:
        return spec.condition or "必要条件を準備できていない"
    return status.value


def build_validation_plan(
    rom_number: int | None,
    *,
    conditions_available: Iterable[str] = (),
) -> tuple[ValidationPlanEntry, ...]:
    conditions = frozenset(conditions_available)
    entries: list[ValidationPlanEntry] = []
    for spec in COMMAND_SPECS:
        status = classify_for_usm02(spec, rom_number, conditions_available=conditions)
        entries.append(
            ValidationPlanEntry(
                section=spec.section,
                name=spec.name,
                command_hex=_hex(spec.command) or "",
                detail_hex=_hex(spec.detail),
                subcommand_hex=_hex(spec.subcommand),
                response_pattern=spec.response_pattern.value,
                ack_data_length=spec.ack_data_length,
                operation=spec.operation.value,
                plan_status=status.value,
                reason=_reason(spec, status),
            )
        )
    if len(entries) != 54:
        raise RuntimeError("検証計画が54件ではありません")
    return tuple(entries)


def summarize_plan(entries: Iterable[ValidationPlanEntry]) -> dict[str, int]:
    entries_tuple = tuple(entries)
    if len(entries_tuple) != 54:
        raise ValueError("集計対象は54件である必要があります")
    return dict(sorted(Counter(entry.plan_status for entry in entries_tuple).items()))


HARD_SAFETY_RULES: tuple[str, ...] = (
    "Kill(7.5.5)は送信しない",
    "Lock(7.5.6)は送信しない",
    "UHF_Encode(7.5.10)は送信しない",
    "FLASH設定初期化(7.3.11)は送信しない",
    "予期しないNACK・timeout・復元失敗で後続送信を停止する",
    "Access/Kill Passwordをログへ出さない",
    "PC/UII/EPC/TIDの実値を共有用ログへ出さない",
    "設定変更は事前読取・同値書込・再読取・復元確認を必須とする",
    "タグ書込は廃棄可能タグのUser領域だけを対象にし、事前読取と復元を必須とする",
)
