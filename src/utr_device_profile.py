#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""実機応答の解釈に必要なリーダライタ状態のスナップショット。"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.utr_antenna import AntennaSwitchingSetting, RomVersionInfo


@dataclass(frozen=True)
class DeviceProfile:
    """ROM、機種、設定値、物理アンテナ状態を混同せず保持する。"""

    model_key: str
    rom: RomVersionInfo
    reader_id: int = 0
    antenna_capacity: int = 4
    configured_antennas: tuple[int, ...] = ()
    connected_antennas: tuple[int, ...] = ()
    antenna_id_output_enabled: bool = False
    inventory_tid_enabled: bool | None = None
    epc_buffering_enabled: bool | None = None
    read_cycle_completion_enabled: bool | None = None
    antenna_switch_completion_enabled: bool | None = None
    carrier_detect_response_enabled: bool | None = None
    source_notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def rom_number(self) -> int:
        """例: 2.052 -> 2052、2.100 -> 2100。"""
        try:
            return int(self.rom.major_version) * 1000 + int(self.rom.minor_version)
        except ValueError as exc:
            raise ValueError(f"ROMバージョンを数値化できません: {self.rom.firmware_version}") from exc

    def validate(self) -> None:
        if self.model_key != "UTR-SUN02-4CH":
            raise ValueError(f"USM02検証対象外の機種です: {self.model_key}")
        if self.rom.series_name != "USM02":
            raise ValueError(f"USM02検証対象外のROMシリーズです: {self.rom.series_name}")
        if self.antenna_capacity != 4:
            raise ValueError("UTR-SUN02-4CHの物理アンテナ容量は4である必要があります")
        valid = set(range(self.antenna_capacity))
        if not set(self.configured_antennas).issubset(valid):
            raise ValueError("設定アンテナ番号が物理容量外です")
        if not set(self.connected_antennas).issubset(valid):
            raise ValueError("接続アンテナ番号が物理容量外です")


def build_usm02_device_profile(
    rom: RomVersionInfo,
    command_mode_antenna_setting: AntennaSwitchingSetting,
    connected_antennas: list[int],
    *,
    reader_id: int = 0,
    inventory_tid_enabled: bool | None = None,
    epc_buffering_enabled: bool | None = None,
    read_cycle_completion_enabled: bool | None = None,
    antenna_switch_completion_enabled: bool | None = None,
    carrier_detect_response_enabled: bool | None = None,
) -> DeviceProfile:
    """既存のROM/アンテナ解析結果からUSM02用プロファイルを作る。"""
    profile = DeviceProfile(
        model_key="UTR-SUN02-4CH",
        rom=rom,
        reader_id=reader_id,
        antenna_capacity=4,
        configured_antennas=tuple(command_mode_antenna_setting.enabled_antennas),
        connected_antennas=tuple(sorted(set(connected_antennas))),
        antenna_id_output_enabled=command_mode_antenna_setting.antenna_id_output_enabled,
        inventory_tid_enabled=inventory_tid_enabled,
        epc_buffering_enabled=epc_buffering_enabled,
        read_cycle_completion_enabled=read_cycle_completion_enabled,
        antenna_switch_completion_enabled=antenna_switch_completion_enabled,
        carrier_detect_response_enabled=carrier_detect_response_enabled,
        source_notes=(
            "antenna_capacity=機種仕様",
            "configured_antennas=7.4.5 アンテナ切替設定",
            "connected_antennas=7.3.5 UHF_CheckAntenna",
        ),
    )
    profile.validate()
    return profile
