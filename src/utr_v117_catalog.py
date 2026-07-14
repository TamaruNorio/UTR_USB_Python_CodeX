#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-S201通信プロトコル Ver.1.17 の54コマンド仕様カタログ。

このモジュールは実機通信を行わない。公式説明書6.1/7.3/7.4/7.5の
コマンド集合、応答形態、USM02での適用可否、安全上の保留条件を、
検証プログラムから機械判定できる形で保持する。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResponsePattern(str, Enum):
    """正常系で期待する応答形態。"""

    SINGLE_ACK = "single_ack"
    CONDITIONAL_ACK = "conditional_ack"
    NO_RESPONSE = "no_response"
    MULTI_TAG_THEN_ACK = "multi_tag_then_ack"
    VARIABLE_ACK = "variable_ack"


class OperationKind(str, Enum):
    READ_ONLY = "read_only"
    CONTROL = "control"
    RAM_WRITE = "ram_write"
    FLASH_WRITE = "flash_write"
    RF_READ = "rf_read"
    TAG_WRITE = "tag_write"
    DESTRUCTIVE = "destructive"


class PlanStatus(str, Enum):
    READY = "READY"
    ROM_CHECK_REQUIRED = "ROM_CHECK_REQUIRED"
    NOT_SUPPORTED_BY_DEVICE = "NOT_SUPPORTED_BY_DEVICE"
    NOT_SUPPORTED_BY_ROM = "NOT_SUPPORTED_BY_ROM"
    CONDITION_NOT_AVAILABLE = "CONDITION_NOT_AVAILABLE"
    NOT_EXECUTED_BY_USER_DECISION = "NOT_EXECUTED_BY_USER_DECISION"


@dataclass(frozen=True)
class CommandSpec:
    section: str
    name: str
    command: int
    detail: int | None
    subcommand: int | None
    response_pattern: ResponsePattern
    ack_data_length: str
    operation: OperationKind
    response_detail: int | None = None
    minimum_rom: int | None = None
    usm02_supported: bool = True
    hold_reason: str | None = None
    condition: str | None = None

    @property
    def key(self) -> str:
        return self.section


def _spec(
    section: str,
    name: str,
    command: int,
    detail: int | None,
    response_pattern: ResponsePattern,
    ack_data_length: str,
    operation: OperationKind,
    *,
    subcommand: int | None = None,
    minimum_rom: int | None = None,
    usm02_supported: bool = True,
    hold_reason: str | None = None,
    condition: str | None = None,
    response_detail: int | None = None,
) -> CommandSpec:
    return CommandSpec(
        section=section,
        name=name,
        command=command,
        detail=detail,
        subcommand=subcommand,
        response_pattern=response_pattern,
        ack_data_length=ack_data_length,
        operation=operation,
        response_detail=detail if response_detail is None else response_detail,
        minimum_rom=minimum_rom,
        usm02_supported=usm02_supported,
        hold_reason=hold_reason,
        condition=condition,
    )


# ack_data_length はACKフレームのDATA長。可変長は式で表す。
COMMAND_SPECS: tuple[CommandSpec, ...] = (
    # 7.3 リーダライタ制御コマンド（12件）
    _spec("7.3.1", "エラー情報の読み取り", 0x4F, 0x80, ResponsePattern.SINGLE_ACK, "04", OperationKind.READ_ONLY),
    _spec("7.3.2", "ブザーの制御", 0x42, None, ResponsePattern.CONDITIONAL_ACK, "00 (応答要求=1)", OperationKind.CONTROL),
    _spec("7.3.3", "LED&ブザーの制御", 0x4E, 0x57, ResponsePattern.SINGLE_ACK, "01", OperationKind.CONTROL),
    _spec("7.3.4", "RF送信信号の制御", 0x4E, 0x9E, ResponsePattern.SINGLE_ACK, "02", OperationKind.CONTROL),
    _spec("7.3.5", "UHF_CheckAntenna", 0x55, 0x44, ResponsePattern.SINGLE_ACK, "03", OperationKind.READ_ONLY),
    _spec("7.3.6", "使用アンテナ番号の読み取り", 0x55, 0x48, ResponsePattern.SINGLE_ACK, "04", OperationKind.READ_ONLY, usm02_supported=False),
    _spec("7.3.7", "使用アンテナ番号の書き込み", 0x55, 0x38, ResponsePattern.SINGLE_ACK, "04", OperationKind.RAM_WRITE, usm02_supported=False, response_detail=0x48),
    _spec("7.3.8", "ROMバージョンの読み取り", 0x4F, 0x90, ResponsePattern.SINGLE_ACK, "0A", OperationKind.READ_ONLY),
    _spec("7.3.9", "チップバージョンの読み取り", 0x55, 0x90, ResponsePattern.VARIABLE_ACK, "0B(ファームウェア) / 0C(シリアル)", OperationKind.READ_ONLY),
    _spec("7.3.10", "リスタート", 0x4E, 0x9D, ResponsePattern.NO_RESPONSE, "応答なし", OperationKind.CONTROL),
    _spec(
        "7.3.11", "FLASH設定の初期化", 0x4E, 0x6F, ResponsePattern.SINGLE_ACK, "01", OperationKind.FLASH_WRITE,
        hold_reason="FLASH全設定を初期化するため実行しない",
    ),
    _spec("7.3.12", "UHF_GetHandle", 0x55, 0x46, ResponsePattern.SINGLE_ACK, "03", OperationKind.RF_READ, minimum_rom=2050),

    # 7.4 リーダライタ設定コマンド（31件）
    _spec("7.4.1", "リーダライタ動作モードの読み取り", 0x4F, 0x00, ResponsePattern.SINGLE_ACK, "09", OperationKind.READ_ONLY),
    _spec("7.4.2", "UHF_GetSelectParam", 0x55, 0x40, ResponsePattern.VARIABLE_ACK, "9+n", OperationKind.READ_ONLY),
    _spec("7.4.3", "UHF_GetInventoryParam", 0x55, 0x41, ResponsePattern.SINGLE_ACK, "0B", OperationKind.READ_ONLY),
    _spec("7.4.4", "UHF_GetExpandSelectParam", 0x55, 0x42, ResponsePattern.VARIABLE_ACK, "23*n+2", OperationKind.READ_ONLY),
    _spec("7.4.5", "アンテナ切替設定の読み取り", 0x55, 0x43, ResponsePattern.SINGLE_ACK, "08", OperationKind.READ_ONLY, subcommand=0x00),
    _spec("7.4.6", "出力設定の読み取り", 0x55, 0x43, ResponsePattern.SINGLE_ACK, "0B", OperationKind.READ_ONLY, subcommand=0x01),
    _spec("7.4.7", "周波数設定の読み取り", 0x55, 0x43, ResponsePattern.SINGLE_ACK, "0C", OperationKind.READ_ONLY, subcommand=0x02),
    _spec("7.4.8", "RFタグ通信関連パラメータの読み取り", 0x55, 0x43, ResponsePattern.SINGLE_ACK, "06", OperationKind.READ_ONLY, subcommand=0x04),
    _spec("7.4.9", "EPC(UII)関連パラメータの読み取り", 0x55, 0x43, ResponsePattern.SINGLE_ACK, "04", OperationKind.READ_ONLY, subcommand=0x05),
    _spec("7.4.10", "外部アンテナ自動切替設定の読み取り", 0x55, 0x47, ResponsePattern.SINGLE_ACK, "0C", OperationKind.READ_ONLY, usm02_supported=False),
    _spec("7.4.11", "汎用ポート値の読み取り", 0x4F, 0x9F, ResponsePattern.SINGLE_ACK, "05", OperationKind.READ_ONLY),
    _spec("7.4.12", "拡張ポート値の読み取り", 0x4F, 0xA0, ResponsePattern.SINGLE_ACK, "05", OperationKind.READ_ONLY, usm02_supported=False),
    _spec("7.4.13", "FLASH設定値の読み取り(1バイトアクセス)", 0x4F, 0xB4, ResponsePattern.SINGLE_ACK, "02", OperationKind.READ_ONLY),
    _spec("7.4.14", "RSSIフィルタ設定の読み取り", 0x55, 0x49, ResponsePattern.VARIABLE_ACK, "12*n+5", OperationKind.READ_ONLY, minimum_rom=2100),
    _spec("7.4.15", "アンテナ個別送信出力設定の読み取り", 0x55, 0x4A, ResponsePattern.VARIABLE_ACK, "5+n", OperationKind.READ_ONLY, minimum_rom=2100),
    _spec("7.4.16", "リーダライタ動作モードの書き込み", 0x4E, 0x00, ResponsePattern.SINGLE_ACK, "00", OperationKind.RAM_WRITE, subcommand=0x10),
    _spec("7.4.17", "UHF_SetSelectParam", 0x55, 0x30, ResponsePattern.SINGLE_ACK, "01", OperationKind.RAM_WRITE),
    _spec("7.4.18", "UHF_SetInventoryParam", 0x55, 0x31, ResponsePattern.SINGLE_ACK, "01", OperationKind.RAM_WRITE),
    _spec("7.4.19", "UHF_SetExpandSelectParam", 0x55, 0x32, ResponsePattern.SINGLE_ACK, "01", OperationKind.RAM_WRITE),
    _spec("7.4.20", "アンテナ切替設定の書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "08", OperationKind.RAM_WRITE, subcommand=0x00),
    _spec("7.4.21", "出力設定の書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "0B", OperationKind.RAM_WRITE, subcommand=0x01),
    _spec("7.4.22", "周波数設定の書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "0C", OperationKind.RAM_WRITE, subcommand=0x02),
    _spec("7.4.23", "Accessパスワードの書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "03", OperationKind.RAM_WRITE, subcommand=0x03),
    _spec("7.4.24", "RFタグ通信関連パラメータの書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "03", OperationKind.RAM_WRITE, subcommand=0x04),
    _spec("7.4.25", "EPC(UII)関連パラメータの書き込み", 0x55, 0x33, ResponsePattern.SINGLE_ACK, "04", OperationKind.RAM_WRITE, subcommand=0x05),
    _spec("7.4.26", "外部アンテナ自動切替設定の書き込み", 0x55, 0x37, ResponsePattern.SINGLE_ACK, "0C", OperationKind.RAM_WRITE, usm02_supported=False),
    _spec("7.4.27", "汎用ポート値の書き込み", 0x4E, 0x9F, ResponsePattern.SINGLE_ACK, "01", OperationKind.RAM_WRITE),
    _spec("7.4.28", "拡張ポート値の書き込み", 0x4E, 0xA0, ResponsePattern.SINGLE_ACK, "01", OperationKind.RAM_WRITE, usm02_supported=False),
    _spec("7.4.29", "FLASH設定値の書き込み(1バイトアクセス)", 0x4E, 0xB4, ResponsePattern.SINGLE_ACK, "01", OperationKind.FLASH_WRITE),
    _spec("7.4.30", "RSSIフィルタ設定の書き込み", 0x55, 0x39, ResponsePattern.SINGLE_ACK, "05", OperationKind.RAM_WRITE, minimum_rom=2100),
    _spec("7.4.31", "アンテナ個別送信出力設定の書き込み", 0x55, 0x3A, ResponsePattern.SINGLE_ACK, "05", OperationKind.RAM_WRITE, minimum_rom=2100),

    # 7.5 RFタグ通信コマンド（11件）
    _spec("7.5.1", "UHF_Inventory", 0x55, 0x10, ResponsePattern.MULTI_TAG_THEN_ACK, "TAG:5+n / 完了ACK:05", OperationKind.RF_READ),
    _spec("7.5.2", "UHF_InventoryRead", 0x55, 0x14, ResponsePattern.MULTI_TAG_THEN_ACK, "TAG:7+n1+n2+n3 / 完了ACK:05", OperationKind.RF_READ),
    _spec("7.5.3", "UHF_Read", 0x55, 0x15, ResponsePattern.VARIABLE_ACK, "n+2", OperationKind.RF_READ),
    _spec("7.5.4", "UHF_Write", 0x55, 0x16, ResponsePattern.SINGLE_ACK, "01", OperationKind.TAG_WRITE),
    _spec(
        "7.5.5", "UHF_Kill", 0x55, 0x17, ResponsePattern.SINGLE_ACK, "01", OperationKind.DESTRUCTIVE,
        hold_reason="ユーザー指定によりKillは実行しない",
    ),
    _spec(
        "7.5.6", "UHF_Lock", 0x55, 0x18, ResponsePattern.SINGLE_ACK, "01", OperationKind.DESTRUCTIVE,
        hold_reason="ユーザー指定によりLockは実行しない",
    ),
    _spec("7.5.7", "UHF_BlockWrite", 0x55, 0x1A, ResponsePattern.SINGLE_ACK, "01", OperationKind.TAG_WRITE),
    _spec("7.5.8", "UHF_BlockErase", 0x55, 0x1B, ResponsePattern.SINGLE_ACK, "01", OperationKind.TAG_WRITE),
    _spec("7.5.9", "UHF_BlockWrite2", 0x55, 0x1D, ResponsePattern.SINGLE_ACK, "01", OperationKind.TAG_WRITE),
    _spec(
        "7.5.10", "UHF_Encode", 0x55, 0x1E, ResponsePattern.SINGLE_ACK, "01", OperationKind.DESTRUCTIVE,
        hold_reason="複数領域変更とLockを含み得るため実行しない",
    ),
    _spec(
        "7.5.11", "UHF_ThroughCmd", 0x55, 0xFF, ResponsePattern.VARIABLE_ACK, "1..255", OperationKind.RF_READ,
        minimum_rom=2050,
        condition="TIDでタグICを特定し、そのIC向けの安全なコマンド仕様を用意できた場合のみ",
    ),
)


def get_command_spec(section: str) -> CommandSpec:
    """PDF節番号で1件を取得する。"""
    for spec in COMMAND_SPECS:
        if spec.section == section:
            return spec
    raise KeyError(section)


def classify_for_usm02(
    spec: CommandSpec,
    rom_number: int | None,
    *,
    conditions_available: frozenset[str] = frozenset(),
) -> PlanStatus:
    """USM02での実機検証可否を安全側に分類する。"""
    if not spec.usm02_supported:
        return PlanStatus.NOT_SUPPORTED_BY_DEVICE
    if rom_number is None and spec.minimum_rom is not None:
        return PlanStatus.ROM_CHECK_REQUIRED
    if spec.minimum_rom is not None and rom_number < spec.minimum_rom:
        return PlanStatus.NOT_SUPPORTED_BY_ROM
    if spec.hold_reason is not None:
        return PlanStatus.NOT_EXECUTED_BY_USER_DECISION
    if spec.condition is not None and spec.section not in conditions_available:
        return PlanStatus.CONDITION_NOT_AVAILABLE
    return PlanStatus.READY


def validate_catalog() -> None:
    """件数、節番号、コマンド識別子の基本整合性を検査する。"""
    if len(COMMAND_SPECS) != 54:
        raise ValueError(f"command catalog must contain 54 entries: {len(COMMAND_SPECS)}")
    sections = [spec.section for spec in COMMAND_SPECS]
    if len(set(sections)) != len(sections):
        raise ValueError("duplicate PDF section in command catalog")
    for spec in COMMAND_SPECS:
        for name, value in (("command", spec.command), ("detail", spec.detail), ("subcommand", spec.subcommand)):
            if value is not None and not 0 <= value <= 0xFF:
                raise ValueError(f"{spec.section}: {name} is not a byte")


validate_catalog()
