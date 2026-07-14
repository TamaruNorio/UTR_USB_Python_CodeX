#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02のアンテナ別Inventoryとタグ検出時ブザー確認。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.utr_commands import BUZZER_SOUND_PIPIPI, build_buzzer_command, build_frame
from src.utr_device_profile import DeviceProfile
from src.utr_response_v117 import AddressRole, VerificationResult, interpret_address, verify_command_response
from src.utr_usm02_safe_controls import (
    Exchange,
    clear_before_restore,
    read_command_mode_antenna_setting,
    verify_ack,
    write_command_mode_antenna_setting,
)
from src.utr_v117_catalog import get_command_spec


@dataclass(frozen=True)
class AntennaInventoryBuzzerResult:
    antenna: int
    tag_detected: bool
    tag_response_count: int
    unique_tag_count: int
    completion_reported_count: int
    response_count_matches_completion: bool
    observed_channel: int
    buzzer_command_sent: bool
    buzzer_ack_verified: bool


@dataclass(frozen=True)
class SequentialInventoryBuzzerResult:
    requested_antennas: tuple[int, ...]
    original_antennas: tuple[int, ...]
    antenna_results: tuple[AntennaInventoryBuzzerResult, ...]
    antenna_restored: bool
    inventory_execution_count: int
    buzzer_ack_count: int
    flash_write_executed: bool = False
    tag_memory_write_executed: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_target_antennas(
    antennas: tuple[int, ...] | list[int],
    antenna_capacity: int,
) -> tuple[int, ...]:
    """指定順を保持したまま、重複・物理容量外を拒否する。"""
    normalized = tuple(antennas)
    if not normalized:
        raise ValueError("対象アンテナを1件以上指定してください")
    if len(set(normalized)) != len(normalized):
        raise ValueError("対象アンテナに重複があります")
    invalid = tuple(value for value in normalized if value < 0 or value >= antenna_capacity)
    if invalid:
        raise ValueError(f"物理容量外のアンテナ番号です: {list(invalid)}")
    return normalized


def _tag_identity(frame_data: bytes) -> bytes:
    """タグ固有値を外部へ返さず、メモリ上の重複判定キーだけを切り出す。"""
    if len(frame_data) < 5:
        raise RuntimeError("Inventoryタグ応答のDATA長が不足しています")
    pc_uii_length = frame_data[4]
    if pc_uii_length == 0:
        raise RuntimeError("Inventoryタグ応答のPC+UII長が0です")
    end = 5 + pc_uii_length
    if len(frame_data) < end:
        raise RuntimeError("Inventoryタグ応答のPC+UII長とDATA長が一致しません")
    return frame_data[5:end]


def _inventory_once(
    ser,
    exchange: Exchange,
    profile: DeviceProfile,
    target_antenna: int,
) -> tuple[int, int, int, bool, int]:
    response = exchange(ser, build_frame(0x55, b"\x10"))
    verification = verify_command_response(get_command_spec("7.5.1"), response, profile)
    if verification.result != VerificationResult.MULTI_RESPONSE_VERIFIED:
        raise RuntimeError(
            "7.5.1 応答異常: "
            f"{verification.result.value}; {' / '.join(verification.notes)}"
        )

    tag_frames = verification.frames[:-1]
    completion = verification.frames[-1]
    unique_tags: set[bytes] = set()
    for frame in tag_frames:
        address = interpret_address(frame, profile)
        if address.role != AddressRole.ANTENNA_NUMBER:
            raise RuntimeError("タグ応答2バイト目をアンテナ番号として確定できません")
        if address.value != target_antenna:
            raise RuntimeError(
                f"タグ応答アンテナが選択中のANT{target_antenna}と一致しません: "
                f"ANT{address.value}"
            )
        unique_tags.add(_tag_identity(frame.data))

    completion_count = int.from_bytes(completion.data[2:4], byteorder="little")
    observed_channel = completion.data[4]
    tag_response_count = len(tag_frames)
    return (
        tag_response_count,
        len(unique_tags),
        completion_count,
        tag_response_count == completion_count,
        observed_channel,
    )


def execute_sequential_inventory_buzzer(
    ser,
    profile: DeviceProfile,
    exchange: Exchange,
    *,
    target_antennas: tuple[int, ...] = (0, 1, 2),
) -> SequentialInventoryBuzzerResult:
    """ANTを順次選び、タグ応答があったANTだけブザーを鳴らして復元する。"""
    profile.validate()
    targets = normalize_target_antennas(target_antennas, profile.antenna_capacity)
    missing = tuple(antenna for antenna in targets if antenna not in profile.connected_antennas)
    if missing:
        raise ValueError(
            "UHF_CheckAntennaで接続OKではない対象があります: "
            + ", ".join(f"ANT{value}" for value in missing)
        )
    if profile.antenna_id_output_enabled is not True:
        raise ValueError("アンテナID出力がONではないため、タグ応答ANTを判定できません")
    if profile.epc_buffering_enabled is not False:
        raise ValueError(
            "EPCバッファリングがOFFと確認できないため、直接タグ応答を判定できません"
        )

    original = read_command_mode_antenna_setting(ser, exchange, profile)
    if original.antenna_id_output_enabled is not True:
        raise RuntimeError("実行直前のアンテナID出力がONではないため停止します")
    if original.antenna_mask == 0:
        raise RuntimeError("実行直前の使用アンテナ設定が0件のため停止します")

    current_mask = original.antenna_mask
    write_attempted = False
    results: list[AntennaInventoryBuzzerResult] = []
    primary_error: Exception | None = None
    restore_error: Exception | None = None
    restored = False

    try:
        for antenna in targets:
            target_mask = 1 << antenna
            if current_mask != target_mask:
                # ACK後の読戻しで失敗しても実機設定は変化した可能性があるため、
                # 送信前に復元対象として記録する。
                write_attempted = True
                write_command_mode_antenna_setting(
                    ser,
                    exchange,
                    profile,
                    original,
                    target_mask,
                )
                current_mask = target_mask

            (
                tag_response_count,
                unique_tag_count,
                completion_count,
                count_matches,
                observed_channel,
            ) = _inventory_once(ser, exchange, profile, antenna)
            tag_detected = tag_response_count > 0
            buzzer_verified = False
            if tag_detected:
                buzzer_response = exchange(
                    ser,
                    build_buzzer_command(
                        response_required=True,
                        sound_type=BUZZER_SOUND_PIPIPI,
                    ),
                )
                verify_ack("7.3.2", buzzer_response, profile)
                buzzer_verified = True

            results.append(
                AntennaInventoryBuzzerResult(
                    antenna=antenna,
                    tag_detected=tag_detected,
                    tag_response_count=tag_response_count,
                    unique_tag_count=unique_tag_count,
                    completion_reported_count=completion_count,
                    response_count_matches_completion=count_matches,
                    observed_channel=observed_channel,
                    buzzer_command_sent=tag_detected,
                    buzzer_ack_verified=buzzer_verified,
                )
            )
    except Exception as exc:
        primary_error = exc
    finally:
        if write_attempted:
            try:
                clear_before_restore(ser)
                readback = write_command_mode_antenna_setting(
                    ser,
                    exchange,
                    profile,
                    original,
                    original.antenna_mask,
                )
                restored = readback.antenna_mask == original.antenna_mask
                if not restored:
                    raise RuntimeError("アンテナ復元後の読戻しが開始値と一致しません")
            except Exception as exc:
                restore_error = exc
        else:
            restored = True

    if restore_error is not None:
        suffix = "" if primary_error is None else f" / 実行時エラー: {primary_error}"
        raise RuntimeError(f"アンテナ復元失敗: {restore_error}{suffix}")
    if primary_error is not None:
        raise primary_error

    return SequentialInventoryBuzzerResult(
        requested_antennas=targets,
        original_antennas=tuple(original.enabled_antennas),
        antenna_results=tuple(results),
        antenna_restored=restored,
        inventory_execution_count=len(results),
        buzzer_ack_count=sum(result.buzzer_ack_verified for result in results),
    )
