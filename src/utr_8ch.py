#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向けの補助関数。

このモジュールは、8CH機の機種判定、表示文言、Inventory用アンテナ選択、
使用アンテナ番号設定コマンドのdry-run生成を扱います。

重要:
- 実機通信は行いません。
- アンテナ切替設定の書き込みは行いません。
- Inventoryコマンドは送信しません。
- FLASHは変更しません。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from src.utr_antenna import AntennaCheckTarget
    from src.utr_commands import PARAMETER_KIND_COMMAND_MODE, build_frame
except ModuleNotFoundError:
    from utr_antenna import AntennaCheckTarget
    from utr_commands import PARAMETER_KIND_COMMAND_MODE, build_frame

EIGHT_CH_MODEL_KEYS = frozenset({"UTR-SUN02V-8CH", "UTR-SUN02-8CH"})
DETAIL_USAGE_ANTENNA_NUMBER_WRITE = 0x38
SUN02_8CH_EXTERNAL_ANTENNA_NUMBER = 0x00

# UTR-SUN02-8CHの使用アンテナ番号系です。
# UHF_CheckAntennaの番号 00h〜07h はANT1〜ANT8ですが、使用アンテナ番号系では
# ANT1=00h, ANT2=20h, ..., ANT8=E0h として扱います。
SUN02_8CH_USAGE_ANTENNA_NUMBER_BY_PORT: dict[int, int] = {
    1: 0x00,
    2: 0x20,
    3: 0x40,
    4: 0x60,
    5: 0x80,
    6: 0xA0,
    7: 0xC0,
    8: 0xE0,
}


@dataclass(frozen=True)
class EightChInventoryTarget:
    """8CH Inventoryで選択されたアンテナ候補。

    check_target:
        UHF_CheckAntennaで接続OKだった対象。
    physical_port:
        物理ポート番号。ANT1なら1、ANT8なら8。
    usage_antenna_number:
        UTR-SUN02-8CHの使用アンテナ番号系。ANT1なら0x00、ANT8なら0xE0。
    """

    check_target: AntennaCheckTarget
    physical_port: int
    usage_antenna_number: int

    @property
    def label(self) -> str:
        return f"ANT{self.physical_port}"

    @property
    def usage_antenna_number_hex(self) -> str:
        return f"{self.usage_antenna_number:02X}h"


@dataclass(frozen=True)
class EightChUsageAntennaCommandDryRun:
    """8CH使用アンテナ番号設定コマンドのdry-run情報。"""

    target: EightChInventoryTarget
    parameter_kind: int
    internal_antenna_number: int
    external_antenna_number: int
    frame: bytes

    @property
    def internal_antenna_number_hex(self) -> str:
        return f"{self.internal_antenna_number:02X}h"

    @property
    def external_antenna_number_hex(self) -> str:
        return f"{self.external_antenna_number:02X}h"

    @property
    def frame_hex(self) -> str:
        return self.frame.hex(" ").upper()


def is_8ch_model_key(model_key: str | None) -> bool:
    """仕様書照合機種キーが8CH機か判定します。"""
    return model_key in EIGHT_CH_MODEL_KEYS


def format_8ch_diagnostic_notes(model_key: str | None) -> list[str]:
    """8CH診断時に表示する注意点を返します。"""
    if model_key == "UTR-SUN02-8CH":
        return [
            "8CH機種: UTR-SUN02-8CH（外付け8CH）",
            "UHF_CheckAntennaでは 00h〜07h が ANT1〜ANT8 に対応します。",
            "使用アンテナ番号系では ANT1=00h, ANT2=20h, ..., ANT8=E0h として扱います。",
            "本診断では接続確認だけを行い、アンテナ切替設定やFLASHは変更しません。",
        ]
    if model_key == "UTR-SUN02V-8CH":
        return [
            "8CH機種: UTR-SUN02V-8CH（外部アンテナユニット対応8CH）",
            "UHF_CheckAntennaでは 00h〜07h が ANT1〜ANT8 に対応します。",
            "使用アンテナ番号系では 内部アンテナ番号×32+外部アンテナ番号 の体系を使います。",
            "本診断では接続確認だけを行い、アンテナ切替設定やFLASHは変更しません。",
        ]
    return [
        "8CH機ではないため、8CH専用診断は実行しません。",
    ]


def check_antenna_number_to_physical_port(check_antenna_number: int) -> int:
    """UHF_CheckAntennaの番号をANT1〜ANT8の物理ポート番号へ変換します。"""
    if not 0 <= check_antenna_number <= 7:
        raise ValueError("check_antenna_number must be in range 0-7")
    return check_antenna_number + 1


def physical_port_to_sun02_8ch_internal_antenna_number(physical_port: int) -> int:
    """UTR-SUN02-8CHの物理ポート番号を内部アンテナ番号へ変換します。

    ANT1=0、ANT3=2、ANT8=7です。
    外部アンテナ番号はUTR-SUN02-8CHでは0固定です。
    """
    if not 1 <= physical_port <= 8:
        raise ValueError("physical_port must be in range 1-8")
    return physical_port - 1


def physical_port_to_sun02_8ch_usage_antenna_number(physical_port: int) -> int:
    """UTR-SUN02-8CHの物理ポート番号を使用アンテナ番号系へ変換します。"""
    try:
        return SUN02_8CH_USAGE_ANTENNA_NUMBER_BY_PORT[physical_port]
    except KeyError as exc:
        raise ValueError("physical_port must be in range 1-8") from exc


def build_8ch_inventory_target(check_target: AntennaCheckTarget) -> EightChInventoryTarget:
    """UHF_CheckAntennaの接続OK対象から、8CH Inventory候補を作成します。"""
    physical_port = check_antenna_number_to_physical_port(check_target.number)
    usage_antenna_number = physical_port_to_sun02_8ch_usage_antenna_number(physical_port)
    return EightChInventoryTarget(
        check_target=check_target,
        physical_port=physical_port,
        usage_antenna_number=usage_antenna_number,
    )


def build_8ch_inventory_targets(check_targets: list[AntennaCheckTarget]) -> list[EightChInventoryTarget]:
    """接続OKだったUHF_CheckAntenna対象を、8CH Inventory候補へ変換します。"""
    return [build_8ch_inventory_target(target) for target in check_targets]


def build_sun02_8ch_usage_antenna_command_dry_run(
    target: EightChInventoryTarget,
    parameter_kind: int = PARAMETER_KIND_COMMAND_MODE,
) -> EightChUsageAntennaCommandDryRun:
    """UTR-SUN02-8CHの使用アンテナ番号設定コマンドをdry-run生成します。

    この関数はフレームを生成するだけで、実機送信は行いません。
    UTR-SUN02-8CHでは外部アンテナ番号を00h固定にします。
    """
    internal_antenna_number = physical_port_to_sun02_8ch_internal_antenna_number(target.physical_port)
    external_antenna_number = SUN02_8CH_EXTERNAL_ANTENNA_NUMBER
    frame = build_frame(
        0x55,
        bytes([
            DETAIL_USAGE_ANTENNA_NUMBER_WRITE,
            parameter_kind,
            internal_antenna_number,
            external_antenna_number,
        ]),
    )
    return EightChUsageAntennaCommandDryRun(
        target=target,
        parameter_kind=parameter_kind,
        internal_antenna_number=internal_antenna_number,
        external_antenna_number=external_antenna_number,
        frame=frame,
    )


def format_8ch_usage_antenna_command_dry_run(dry_run: EightChUsageAntennaCommandDryRun) -> list[str]:
    """使用アンテナ番号設定コマンドのdry-run情報を画面表示用に整形します。"""
    return [
        f"対象アンテナ: {dry_run.target.label}",
        f"使用アンテナ番号: {dry_run.target.usage_antenna_number_hex}",
        f"内部アンテナ番号: {dry_run.internal_antenna_number_hex}",
        f"外部アンテナ番号: {dry_run.external_antenna_number_hex}",
        f"dry-run送信フレーム: {dry_run.frame_hex}",
        "注意: この段階ではフレーム表示だけです。実機へは送信しません。",
    ]


def format_8ch_inventory_candidate(target: EightChInventoryTarget) -> str:
    """8CH Inventory候補を画面表示用の1行に変換します。"""
    return f"[{target.physical_port}] {target.label}（使用アンテナ番号: {target.usage_antenna_number_hex}）"


def parse_8ch_inventory_selection_input(
    available_targets: list[EightChInventoryTarget],
    value: str,
) -> Optional[list[EightChInventoryTarget]]:
    """8CH Inventory対象アンテナの入力文字列を解析します。

    対応入力:
        q      : 選択中止
        1      : ANT1だけ選択
        1,2    : ANT1、ANT2を順番に選択
        all    : 候補アンテナをすべて選択

    Returns:
        list[EightChInventoryTarget] | None:
            選択されたアンテナ一覧。q の場合は None。
    """
    normalized = value.strip().lower()
    if normalized in {"q", "quit", "cancel"}:
        return None
    if normalized == "all":
        return list(available_targets)
    if normalized == "":
        raise ValueError("空入力です。例: 1 / 1,2 / all")

    target_by_port = {target.physical_port: target for target in available_targets}
    selected_targets: list[EightChInventoryTarget] = []
    selected_ports: set[int] = set()

    for part in normalized.split(","):
        part = part.strip()
        if part == "":
            raise ValueError("カンマの前後にアンテナ番号を入力してください。")
        try:
            selected_port = int(part)
        except ValueError as exc:
            raise ValueError("アンテナ番号は数値、または all で入力してください。") from exc
        if selected_port not in target_by_port:
            raise ValueError("候補に表示されているANT番号を入力してください。")
        if selected_port not in selected_ports:
            selected_targets.append(target_by_port[selected_port])
            selected_ports.add(selected_port)

    if not selected_targets:
        raise ValueError("Inventoryに使用するアンテナが選択されていません。")
    return selected_targets
