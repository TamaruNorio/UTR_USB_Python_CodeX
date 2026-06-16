#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-S201シリーズのアンテナ関連ヘルパー。

このモジュールでは、アンテナ接続確認とアンテナ番号体系を扱います。

重要:
    「アンテナ番号」はコマンドにより意味が異なります。

    UHF_CheckAntenna:
        接続確認対象の番号です。
        UTR-SUN02-4CH は 0x00〜0x03。
        UTR-SUN02V-8CH / UTR-SUN02-8CH は 0x00〜0x07。

    使用アンテナ番号の読み取り/書き込み:
        8CH機では内部アンテナ番号と外部アンテナ番号の体系を持ちます。
        UTR-SUN02-8CHでは、プロトコル上のアンテナ番号が
        0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0 になります。

    アンテナ切替設定 55 43 / 55 33:
        主にAnt0〜Ant3のビットマスク系です。
        アンテナポート8CH仕様では、55 33の書き込みは無効/NACK対象です。

今回のPRでは、設定書き込みは行いません。
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from src.utr_protocol import calculate_sum_value
except ModuleNotFoundError:
    from utr_protocol import calculate_sum_value


STX = 0x02
ACK = 0x30
ETX = 0x03
CR = 0x0D

DETAIL_ROM_VERSION_READ = 0x90
DETAIL_ANTENNA_SWITCHING_SETTING_READ = 0x43
DETAIL_CHECK_ANTENNA = 0x44

CHECK_STATUS_OK = 0x00
CHECK_STATUS_CONNECTION_ERROR = 0x01
CHECK_STATUS_PARAMETER_ERROR = 0x02

PARAMETER_KIND_LABELS = {
    0x00: "コマンドモード用パラメータ",
    0x01: "自動読み取りモード用パラメータ",
    0x02: "FLASHデータ",
}

SWITCHING_MODE_LABELS = {
    0x00: "制御しない",
    0x01: "制御する",
    0x02: "制御する（複数アンテナ対応）",
}


@dataclass(frozen=True)
class RomVersionInfo:
    """ROMバージョン読み取り結果。

    例:
        2052USM02

    意味:
        2       = メジャーバージョン
        052     = マイナーバージョン
        USM02   = ROMシリーズ名コード

    ROMシリーズ名コードは、仕様書上の機種対応表と照合して機種を確定します。
    """

    raw_text: str
    major_version: str
    minor_version: str
    series_name: str

    @property
    def firmware_version(self) -> str:
        """画面表示用のファームウェアバージョン文字列を返します。"""
        return f"{self.major_version}.{self.minor_version}"


@dataclass(frozen=True)
class AntennaCheckTarget:
    """UHF_CheckAntennaで確認する1つのアンテナ対象。"""

    number: int
    label: str
    description: str


@dataclass(frozen=True)
class AntennaModelProfile:
    """機種ごとのアンテナ体系。"""

    key: str
    display_name: str
    check_targets: tuple[AntennaCheckTarget, ...]
    note: str
    supports_antenna_switching_setting: bool


@dataclass(frozen=True)
class AntennaSwitchingSetting:
    """アンテナ切替設定 55 43 00 の解析結果。"""

    parameter_kind: int
    switching_mode: int
    antenna_id_output_enabled: bool
    antenna_mask: int
    reserved: bytes
    raw: bytes

    @property
    def parameter_kind_label(self) -> str:
        return PARAMETER_KIND_LABELS.get(self.parameter_kind, f"不明(0x{self.parameter_kind:02X})")

    @property
    def switching_mode_label(self) -> str:
        return SWITCHING_MODE_LABELS.get(self.switching_mode, f"不明(0x{self.switching_mode:02X})")

    @property
    def enabled_antennas(self) -> list[int]:
        return antenna_mask_to_numbers(self.antenna_mask)


@dataclass(frozen=True)
class AntennaCheckResult:
    """UHF_CheckAntennaの解析結果。"""

    antenna_number: int
    status_code: int
    raw: bytes

    @property
    def is_connected(self) -> bool:
        return self.status_code == CHECK_STATUS_OK

    @property
    def status_label(self) -> str:
        if self.status_code == CHECK_STATUS_OK:
            return "接続OK"
        if self.status_code == CHECK_STATUS_CONNECTION_ERROR:
            return "接続エラー"
        if self.status_code == CHECK_STATUS_PARAMETER_ERROR:
            return "パラメータ異常（存在しないアンテナ番号の可能性）"
        return f"不明(0x{self.status_code:02X})"


# ROMシリーズ名コードと機種の対応表です。
# これは推定ではなく、仕様書上の対応表に基づく機種識別に使います。
ROM_SERIES_TO_MODEL_KEY_BY_SPEC: dict[str, str] = {
    "USM01": "UTR-S201",
    "USM02": "UTR-SUN02-4CH",
    "USM05": "UTR-SHR201",
    "USM06": "UTR-SUN02V-8CH",
    "USM08": "UTR-SUN02-8CH",
}


ANTENNA_MODEL_PROFILES: dict[str, AntennaModelProfile] = {
    "UTR-S201": AntennaModelProfile(
        key="UTR-S201",
        display_name="UTR-S201 / UTR-SHR201（1アンテナ）",
        check_targets=(
            AntennaCheckTarget(0x00, "ANT0", "接続アンテナ"),
        ),
        note="UHF_CheckAntennaではANT0のみ確認します。",
        supports_antenna_switching_setting=False,
    ),
    "UTR-SUN02-4CH": AntennaModelProfile(
        key="UTR-SUN02-4CH",
        display_name="UTR-SUN02-4CH（内蔵1CH + 外付け3CH）",
        check_targets=(
            AntennaCheckTarget(0x00, "ANT0", "内蔵アンテナ"),
            AntennaCheckTarget(0x01, "ANT1", "外付けアンテナ1"),
            AntennaCheckTarget(0x02, "ANT2", "外付けアンテナ2"),
            AntennaCheckTarget(0x03, "ANT3", "外付けアンテナ3"),
        ),
        note="4CH機ではANT0が内蔵アンテナ、ANT1〜ANT3が外付けアンテナです。",
        supports_antenna_switching_setting=True,
    ),
    "UTR-SUN02V-8CH": AntennaModelProfile(
        key="UTR-SUN02V-8CH",
        display_name="UTR-SUN02V-8CH（外部アンテナユニット対応8CH）",
        check_targets=tuple(
            AntennaCheckTarget(number, f"ANT{number + 1}", "外部アンテナ")
            for number in range(8)
        ),
        note=(
            "UHF_CheckAntennaでは0x00〜0x07がANT1〜ANT8に対応します。"
            "使用アンテナ番号系では内部アンテナ番号×32+外部アンテナ番号の体系を使います。"
        ),
        supports_antenna_switching_setting=False,
    ),
    "UTR-SUN02-8CH": AntennaModelProfile(
        key="UTR-SUN02-8CH",
        display_name="UTR-SUN02-8CH（外付け8CH）",
        check_targets=tuple(
            AntennaCheckTarget(number, f"ANT{number + 1}", "外付けアンテナ")
            for number in range(8)
        ),
        note=(
            "UHF_CheckAntennaでは0x00〜0x07がANT1〜ANT8に対応します。"
            "使用アンテナ番号系ではANT1=0x00, ANT2=0x20, ..., ANT8=0xE0です。"
            "外部アンテナ番号は0固定として扱います。"
        ),
        supports_antenna_switching_setting=False,
    ),
}


def list_model_profiles() -> list[AntennaModelProfile]:
    """選択可能な機種プロファイル一覧を返します。"""
    return list(ANTENNA_MODEL_PROFILES.values())


def get_model_profile(model_key: str) -> AntennaModelProfile:
    """機種キーからプロファイルを取得します。"""
    try:
        return ANTENNA_MODEL_PROFILES[model_key]
    except KeyError as exc:
        raise ValueError(f"unknown model_key: {model_key}") from exc


def parse_rom_version_response(frame: bytes) -> RomVersionInfo:
    """ROMバージョン読み取りレスポンスを解析します。

    想定DATA部:
        90 major minor1 minor2 minor3 series1 series2 series3 series4 series5

    実機例:
        90 32 30 35 32 55 53 4D 30 32
        → 2052USM02
        → ファームウェア 2.052
        → ROMシリーズ名 USM02
    """
    data = _validate_ack_frame(
        frame=frame,
        expected_detail=DETAIL_ROM_VERSION_READ,
        expected_data_length=10,
    )

    try:
        raw_text = data[1:10].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("ROMバージョン文字列をASCIIとして解析できません。") from exc

    return RomVersionInfo(
        raw_text=raw_text,
        major_version=raw_text[0],
        minor_version=raw_text[1:4],
        series_name=raw_text[4:9],
    )


def identify_model_key_from_rom(rom_info: RomVersionInfo) -> str | None:
    """ROMシリーズ名コードから仕様書上の機種キーを確定します。

    Returns:
        str | None:
            仕様書上の対応表に存在する場合は機種キー。
            未知のROMシリーズ名の場合はNone。

    注意:
        ここでは「推定」ではなく、既知のROMシリーズ名コードと仕様書対応表の照合を行います。
        未知コードの場合は断定しません。
    """
    return ROM_SERIES_TO_MODEL_KEY_BY_SPEC.get(rom_info.series_name)


def format_rom_version_info(rom_info: RomVersionInfo, identified_model_key: str | None = None) -> list[str]:
    """ROMバージョン解析結果を画面表示用の日本語行に変換します。"""
    lines = [
        f"ROMバージョン: {rom_info.raw_text}",
        f"ファームウェアバージョン: {rom_info.firmware_version}",
        f"ROMシリーズ名: {rom_info.series_name}",
    ]

    if identified_model_key is not None:
        profile = get_model_profile(identified_model_key)
        lines.append(f"仕様書照合機種: {profile.display_name}")
    else:
        lines.append("仕様書照合機種: 不明（手動選択してください）")

    return lines


def antenna_mask_to_numbers(mask: int, max_antennas: int = 8) -> list[int]:
    """Ant0〜Ant7のビットマスクをアンテナ番号リストに変換します。"""
    if not 0x00 <= mask <= 0xFF:
        raise ValueError("mask must be in range 0x00-0xFF")
    if not 1 <= max_antennas <= 8:
        raise ValueError("max_antennas must be in range 1-8")

    return [number for number in range(max_antennas) if mask & (1 << number)]


def format_antenna_numbers(numbers: list[int]) -> str:
    """Ant番号リストを表示用文字列に変換します。"""
    if not numbers:
        return "なし"
    return ", ".join(f"Ant{number}" for number in numbers)


def _validate_ack_frame(frame: bytes, expected_detail: int, expected_data_length: int) -> bytes:
    """ACKフレームの基本形式を検証し、DATA部を返します。"""
    if len(frame) < 7:
        raise ValueError("レスポンス長が短すぎます。")
    if frame[0] != STX or frame[-1] != CR:
        raise ValueError("STXまたはCRが一致しません。")

    data_length = frame[3]
    expected_frame_length = 4 + data_length + 3
    if len(frame) != expected_frame_length:
        raise ValueError("データ長とフレーム長が一致しません。")

    etx_index = 4 + data_length
    if frame[etx_index] != ETX:
        raise ValueError("ETX位置が一致しません。")
    if calculate_sum_value(frame[:-2]) != frame[-2]:
        raise ValueError("SUMが一致しません。")
    if frame[2] != ACK:
        raise ValueError("ACKレスポンスではありません。")
    if data_length != expected_data_length:
        raise ValueError(f"データ長が一致しません: expected={expected_data_length}, actual={data_length}")

    data = frame[4:4 + data_length]
    if data[0] != expected_detail:
        raise ValueError(f"詳細コマンドが一致しません: 0x{data[0]:02X}")

    return data


def parse_antenna_switching_setting_response(frame: bytes) -> AntennaSwitchingSetting:
    """アンテナ切替設定の読み取りレスポンスを解析します。

    想定DATA部:
        43 00 parameter_kind flags antenna_mask 00 00 00

    flags:
        bit7      = アンテナID出力
        bit0-bit1 = アンテナ切替方式
    """
    data = _validate_ack_frame(
        frame=frame,
        expected_detail=DETAIL_ANTENNA_SWITCHING_SETTING_READ,
        expected_data_length=8,
    )

    return AntennaSwitchingSetting(
        parameter_kind=data[2],
        switching_mode=data[3] & 0x03,
        antenna_id_output_enabled=bool(data[3] & 0x80),
        antenna_mask=data[4],
        reserved=data[5:8],
        raw=frame,
    )


def format_antenna_switching_setting(setting: AntennaSwitchingSetting) -> list[str]:
    """アンテナ切替設定を日本語表示用の複数行に変換します。"""
    return [
        f"[{setting.parameter_kind_label}]",
        f"アンテナ切替方式: {setting.switching_mode_label}",
        f"アンテナID出力: {'有効' if setting.antenna_id_output_enabled else '無効'}",
        f"使用するアンテナ: {format_antenna_numbers(setting.enabled_antennas)}",
        f"Raw: {setting.raw.hex(' ').upper()}",
    ]


def parse_check_antenna_response(frame: bytes) -> AntennaCheckResult:
    """UHF_CheckAntennaのACKレスポンスを解析します。

    想定DATA部:
        44 antenna_number status

    status:
        00 = アンテナの接続OK
        01 = アンテナの接続エラー
        02 = パラメータ異常
    """
    data = _validate_ack_frame(
        frame=frame,
        expected_detail=DETAIL_CHECK_ANTENNA,
        expected_data_length=3,
    )

    return AntennaCheckResult(
        antenna_number=data[1],
        status_code=data[2],
        raw=frame,
    )


def format_check_antenna_result(result: AntennaCheckResult, profile: AntennaModelProfile | None = None) -> str:
    """UHF_CheckAntenna結果を1行の日本語表示に変換します。"""
    label = f"ANT{result.antenna_number}"
    description = ""

    if profile is not None:
        for target in profile.check_targets:
            if target.number == result.antenna_number:
                label = target.label
                description = f"（{target.description}）"
                break

    return f"{label}{description}: {result.status_label}"
