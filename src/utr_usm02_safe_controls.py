#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02 Phase 2: ブザー・アンテナ・周波数の一時変更と復元。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from src.utr_antenna import (
    AntennaSwitchingSetting,
    parse_antenna_switching_setting_response,
    parse_antenna_switching_setting_write_response,
)
from src.utr_commands import (
    PARAMETER_KIND_COMMAND_MODE,
    build_buzzer_command,
    build_frame,
    build_read_antenna_switching_setting_command,
    build_read_frequency_setting_command,
    build_write_antenna_switching_setting_command,
    build_write_frequency_setting_command,
)
from src.utr_device_profile import DeviceProfile
from src.utr_reader_settings import FrequencySetting, parse_frequency_setting_response
from src.utr_response_v117 import (
    AddressRole,
    VerificationResult,
    interpret_address,
    verify_command_response,
)
from src.utr_v117_catalog import get_command_spec


Exchange = Callable[[object, bytes], bytes]
PREFERRED_TEST_CHANNELS = tuple(range(26, 33))


@dataclass(frozen=True)
class SafeControlsResult:
    buzzer_ack_verified: bool
    original_antenna: tuple[int, ...]
    temporary_antenna: int
    antenna_restored: bool
    original_starting_channel: int
    temporary_starting_channel: int
    enabled_channels_unchanged: bool
    frequency_restored: bool
    rf_transmission_executed: bool = False
    flash_write_executed: bool = False
    inventory_tag_response_count: int = 0
    observed_rf_channel: int | None = None
    observed_tag_antennas: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def choose_temporary_channel(setting: FrequencySetting, requested: int | None = None) -> int:
    """使用許可済みCHから、現在の開始CHとは異なる試験CHを選ぶ。"""
    enabled = tuple(setting.enabled_channels)
    if requested is not None:
        if requested not in enabled:
            raise ValueError(f"指定CH {requested} は現在の使用許可CHではありません")
        if requested == setting.starting_channel:
            raise ValueError("試験CHは現在の開始CHと異なる必要があります")
        return requested

    preferred = [channel for channel in PREFERRED_TEST_CHANNELS if channel in enabled]
    candidates = preferred or list(enabled)
    for channel in candidates:
        if channel != setting.starting_channel:
            return channel
    raise ValueError("現在の開始CH以外に、使用許可済みの試験CHがありません")


def _verify(section: str, response: bytes, profile: DeviceProfile) -> None:
    verification = verify_command_response(get_command_spec(section), response, profile)
    if verification.result != VerificationResult.ACK_VERIFIED:
        raise RuntimeError(
            f"{section} 応答異常: {verification.result.value}; {' / '.join(verification.notes)}"
        )


def _read_antenna_setting(ser, exchange: Exchange, profile: DeviceProfile) -> AntennaSwitchingSetting:
    response = exchange(
        ser,
        build_read_antenna_switching_setting_command(PARAMETER_KIND_COMMAND_MODE),
    )
    _verify("7.4.5", response, profile)
    setting = parse_antenna_switching_setting_response(response)
    if setting.parameter_kind != PARAMETER_KIND_COMMAND_MODE:
        raise RuntimeError("コマンドモード以外のアンテナ設定応答です")
    return setting


def _read_frequency_setting(ser, exchange: Exchange, profile: DeviceProfile) -> FrequencySetting:
    response = exchange(
        ser,
        build_read_frequency_setting_command(PARAMETER_KIND_COMMAND_MODE),
    )
    _verify("7.4.7", response, profile)
    setting = parse_frequency_setting_response(response)["setting"]
    if setting.parameter_kind != PARAMETER_KIND_COMMAND_MODE:
        raise RuntimeError("コマンドモード以外の周波数設定応答です")
    return setting


def _write_antenna(
    ser,
    exchange: Exchange,
    profile: DeviceProfile,
    original: AntennaSwitchingSetting,
    antenna_mask: int,
) -> AntennaSwitchingSetting:
    response = exchange(
        ser,
        build_write_antenna_switching_setting_command(
            parameter_kind=PARAMETER_KIND_COMMAND_MODE,
            switching_mode=original.switching_mode,
            antenna_id_output_enabled=original.antenna_id_output_enabled,
            antenna_mask=antenna_mask,
        ),
    )
    _verify("7.4.20", response, profile)
    acknowledged = parse_antenna_switching_setting_write_response(response)
    if acknowledged.antenna_mask != antenna_mask:
        raise RuntimeError("アンテナ書込ACKの設定値が要求値と一致しません")
    readback = _read_antenna_setting(ser, exchange, profile)
    if (
        readback.antenna_mask != antenna_mask
        or readback.switching_mode != original.switching_mode
        or readback.antenna_id_output_enabled != original.antenna_id_output_enabled
    ):
        raise RuntimeError("アンテナ設定の読戻しが要求値と一致しません")
    return readback


def _write_frequency(
    ser,
    exchange: Exchange,
    profile: DeviceProfile,
    original: FrequencySetting,
    starting_channel: int,
) -> FrequencySetting:
    response = exchange(
        ser,
        build_write_frequency_setting_command(
            parameter_kind=PARAMETER_KIND_COMMAND_MODE,
            starting_channel=starting_channel,
            enabled_channels=original.enabled_channels,
            reserved=original.reserved,
        ),
    )
    _verify("7.4.22", response, profile)
    readback = _read_frequency_setting(ser, exchange, profile)
    if readback.starting_channel != starting_channel:
        raise RuntimeError("周波数設定の開始CH読戻しが要求値と一致しません")
    if readback.enabled_channels != original.enabled_channels:
        raise RuntimeError("周波数設定の使用許可CHが変更されています")
    return readback


def _clear_before_restore(ser) -> None:
    reset = getattr(ser, "reset_input_buffer", None)
    if callable(reset):
        reset()


def execute_safe_controls(
    ser,
    profile: DeviceProfile,
    exchange: Exchange,
    *,
    target_antenna: int = 1,
    requested_channel: int | None = None,
    verify_rf_channel: bool = False,
) -> SafeControlsResult:
    """3操作を行い、例外時を含め周波数→アンテナの順に復元する。"""
    if target_antenna not in profile.connected_antennas:
        raise ValueError(f"ANT{target_antenna} はUHF_CheckAntennaで接続OKではありません")

    original_antenna = _read_antenna_setting(ser, exchange, profile)
    original_frequency = _read_frequency_setting(ser, exchange, profile)
    temporary_channel = choose_temporary_channel(original_frequency, requested_channel)
    temporary_mask = 1 << target_antenna
    if len(original_antenna.enabled_antennas) != 1:
        raise RuntimeError("コマンドモードの使用アンテナが1件ではないため停止します")
    if original_frequency.reserved != b"\x00\x00\x00\x00":
        raise RuntimeError("周波数設定の予約領域が00hではないため書き込みを停止します")
    # 実機へ送信する前に、変更用・復元用フレームの全入力を検証します。
    build_write_frequency_setting_command(
        PARAMETER_KIND_COMMAND_MODE,
        temporary_channel,
        original_frequency.enabled_channels,
        original_frequency.reserved,
    )
    build_write_frequency_setting_command(
        PARAMETER_KIND_COMMAND_MODE,
        original_frequency.starting_channel,
        original_frequency.enabled_channels,
        original_frequency.reserved,
    )

    antenna_restore_needed = False
    frequency_restore_needed = False
    buzzer_verified = False
    antenna_restored = False
    frequency_restored = False
    primary_error: Exception | None = None
    restore_errors: list[str] = []
    inventory_tag_response_count = 0
    observed_rf_channel: int | None = None
    observed_tag_antennas: tuple[int, ...] = ()

    try:
        buzzer_response = exchange(ser, build_buzzer_command(response_required=True, sound_type=0x00))
        _verify("7.3.2", buzzer_response, profile)
        buzzer_verified = True

        if original_antenna.antenna_mask != temporary_mask:
            antenna_restore_needed = True
            _write_antenna(ser, exchange, profile, original_antenna, temporary_mask)

        frequency_restore_needed = True
        _write_frequency(ser, exchange, profile, original_frequency, temporary_channel)

        if verify_rf_channel:
            inventory_response = exchange(ser, build_frame(0x55, b"\x10"))
            inventory = verify_command_response(
                get_command_spec("7.5.1"),
                inventory_response,
                profile,
            )
            if inventory.result != VerificationResult.MULTI_RESPONSE_VERIFIED:
                raise RuntimeError(
                    "7.5.1 応答異常: "
                    f"{inventory.result.value}; {' / '.join(inventory.notes)}"
                )
            tag_frames = inventory.frames[:-1]
            completion = inventory.frames[-1]
            inventory_tag_response_count = len(tag_frames)
            observed_rf_channel = completion.data[4]
            if observed_rf_channel not in original_frequency.enabled_channels:
                raise RuntimeError("Inventory完了ACKの実使用CHが使用許可CH外です")
            antenna_values: list[int] = []
            for frame in tag_frames:
                interpreted = interpret_address(frame, profile)
                if interpreted.role == AddressRole.ANTENNA_NUMBER:
                    antenna_values.append(interpreted.value)
            observed_tag_antennas = tuple(sorted(set(antenna_values)))
            if observed_tag_antennas and observed_tag_antennas != (target_antenna,):
                raise RuntimeError(
                    f"タグ応答のアンテナ番号がANT{target_antenna}と一致しません: "
                    f"{observed_tag_antennas}"
                )
    except Exception as exc:
        primary_error = exc
    finally:
        if frequency_restore_needed:
            try:
                _clear_before_restore(ser)
                restored_frequency = _write_frequency(
                    ser,
                    exchange,
                    profile,
                    original_frequency,
                    original_frequency.starting_channel,
                )
                frequency_restored = (
                    restored_frequency.starting_channel == original_frequency.starting_channel
                    and restored_frequency.enabled_channels == original_frequency.enabled_channels
                )
            except Exception as exc:
                restore_errors.append(f"周波数復元失敗: {exc}")

        if antenna_restore_needed:
            try:
                _clear_before_restore(ser)
                restored_antenna = _write_antenna(
                    ser,
                    exchange,
                    profile,
                    original_antenna,
                    original_antenna.antenna_mask,
                )
                antenna_restored = restored_antenna.antenna_mask == original_antenna.antenna_mask
            except Exception as exc:
                restore_errors.append(f"アンテナ復元失敗: {exc}")
        else:
            antenna_restored = True

    if restore_errors:
        primary = "" if primary_error is None else f" / 実行時エラー: {primary_error}"
        raise RuntimeError(" / ".join(restore_errors) + primary)
    if primary_error is not None:
        raise primary_error

    return SafeControlsResult(
        buzzer_ack_verified=buzzer_verified,
        original_antenna=tuple(original_antenna.enabled_antennas),
        temporary_antenna=target_antenna,
        antenna_restored=antenna_restored,
        original_starting_channel=original_frequency.starting_channel,
        temporary_starting_channel=temporary_channel,
        enabled_channels_unchanged=True,
        frequency_restored=frequency_restored,
        rf_transmission_executed=verify_rf_channel,
        inventory_tag_response_count=inventory_tag_response_count,
        observed_rf_channel=observed_rf_channel,
        observed_tag_antennas=observed_tag_antennas,
    )
