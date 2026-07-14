#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Ver.1.17のACK/NACK/タグ応答を設定依存で検証する純粋ロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from src.utr_device_profile import DeviceProfile
from src.utr_protocol import calculate_sum_value, parse_nack_frame
from src.utr_v117_catalog import CommandSpec, ResponsePattern


class FrameKind(str, Enum):
    ACK = "ACK"
    NACK = "NACK"
    TAG_DATA = "TAG_DATA"
    OTHER = "OTHER"


class AddressRole(str, Enum):
    READER_ID = "reader_id"
    ANTENNA_NUMBER = "antenna_number"


class VerificationResult(str, Enum):
    ACK_VERIFIED = "ACK_VERIFIED"
    NACK_OBSERVED = "NACK_OBSERVED"
    MULTI_RESPONSE_VERIFIED = "MULTI_RESPONSE_VERIFIED"
    NO_RESPONSE_VERIFIED = "NO_RESPONSE_VERIFIED"
    CONDITIONAL_NO_RESPONSE_VERIFIED = "CONDITIONAL_NO_RESPONSE_VERIFIED"
    FAILED_NEEDS_ANALYSIS = "FAILED_NEEDS_ANALYSIS"


@dataclass(frozen=True)
class ParsedFrame:
    raw: bytes
    address: int
    command: int
    data: bytes

    @property
    def kind(self) -> FrameKind:
        return {
            0x30: FrameKind.ACK,
            0x31: FrameKind.NACK,
            0x6C: FrameKind.TAG_DATA,
        }.get(self.command, FrameKind.OTHER)

    @property
    def detail(self) -> int | None:
        return self.data[0] if self.data else None


@dataclass(frozen=True)
class AddressInterpretation:
    value: int
    role: AddressRole
    label: str


@dataclass(frozen=True)
class CommandVerification:
    result: VerificationResult
    frames: tuple[ParsedFrame, ...]
    notes: tuple[str, ...]
    nack: dict[str, object] | None = None


def parse_frame(raw: bytes) -> ParsedFrame:
    """1フレームを構造・SUMまで検証して解析する。"""
    if len(raw) < 7:
        raise ValueError("フレームが短すぎます")
    if raw[0] != 0x02 or raw[-1] != 0x0D:
        raise ValueError("STXまたはCRが一致しません")
    data_length = raw[3]
    if len(raw) != data_length + 7:
        raise ValueError("DATA長とフレーム長が一致しません")
    if raw[4 + data_length] != 0x03:
        raise ValueError("ETX位置が一致しません")
    if calculate_sum_value(raw[:-2]) != raw[-2]:
        raise ValueError("SUMが一致しません")
    return ParsedFrame(raw=raw, address=raw[1], command=raw[2], data=raw[4:4 + data_length])


def split_frames(received: bytes) -> tuple[ParsedFrame, ...]:
    """連結された応答を完全なフレーム列へ分割する。"""
    frames: list[ParsedFrame] = []
    index = 0
    while index < len(received):
        if received[index] != 0x02:
            raise ValueError(f"STX以外の受信データがあります: offset={index}")
        if len(received) - index < 4:
            raise ValueError("末尾に不完全なフレームがあります")
        frame_length = received[index + 3] + 7
        end = index + frame_length
        if end > len(received):
            raise ValueError("末尾に不完全なフレームがあります")
        frames.append(parse_frame(received[index:end]))
        index = end
    return tuple(frames)


def interpret_address(frame: ParsedFrame, profile: DeviceProfile) -> AddressInterpretation:
    """2バイト目を、応答種類とアンテナID出力設定に基づき解釈する。"""
    if frame.kind == FrameKind.TAG_DATA and profile.antenna_id_output_enabled:
        label = f"ANT{frame.address}"
        return AddressInterpretation(frame.address, AddressRole.ANTENNA_NUMBER, label)
    return AddressInterpretation(frame.address, AddressRole.READER_ID, f"Reader ID {frame.address}")


def response_context_notes(profile: DeviceProfile) -> tuple[str, ...]:
    """応答数・順序・長さへ影響する設定を明示する。"""
    def on_off_unknown(value: bool | None) -> str:
        if value is None:
            return "未読取"
        return "ON" if value else "OFF"

    return (
        f"物理アンテナ容量={profile.antenna_capacity}",
        f"設定アンテナ={list(profile.configured_antennas)}",
        f"接続OKアンテナ={list(profile.connected_antennas)}",
        f"アンテナID出力={on_off_unknown(profile.antenna_id_output_enabled)}",
        f"Inventory TID付加={on_off_unknown(profile.inventory_tid_enabled)}",
        f"EPCバッファリング={on_off_unknown(profile.epc_buffering_enabled)}",
        f"読取サイクル完了応答={on_off_unknown(profile.read_cycle_completion_enabled)}",
        f"アンテナ切替完了応答={on_off_unknown(profile.antenna_switch_completion_enabled)}",
        f"キャリア検知応答={on_off_unknown(profile.carrier_detect_response_enabled)}",
    )


def _length_matches(spec: CommandSpec, data: bytes) -> bool:
    """仕様書の固定長・可変長規則を検査する。"""
    length = len(data)
    fixed: dict[str, int] = {
        "7.3.1": 0x04, "7.3.3": 0x01, "7.3.4": 0x02, "7.3.5": 0x03,
        "7.3.6": 0x04, "7.3.7": 0x04, "7.3.8": 0x0A, "7.3.11": 0x01,
        "7.3.12": 0x03, "7.4.1": 0x09, "7.4.3": 0x0B, "7.4.5": 0x08,
        "7.4.6": 0x0B, "7.4.7": 0x0C, "7.4.8": 0x06, "7.4.9": 0x04,
        "7.4.10": 0x0C, "7.4.11": 0x05, "7.4.12": 0x05, "7.4.13": 0x02,
        "7.4.16": 0x00, "7.4.17": 0x01, "7.4.18": 0x01, "7.4.19": 0x01,
        "7.4.20": 0x08, "7.4.21": 0x0B, "7.4.22": 0x0C, "7.4.23": 0x03,
        "7.4.24": 0x03, "7.4.25": 0x04, "7.4.26": 0x0C, "7.4.27": 0x01,
        "7.4.28": 0x01, "7.4.29": 0x01, "7.4.30": 0x05, "7.4.31": 0x05,
        "7.5.4": 0x01, "7.5.5": 0x01, "7.5.6": 0x01, "7.5.7": 0x01,
        "7.5.8": 0x01, "7.5.9": 0x01, "7.5.10": 0x01,
    }
    if spec.section in fixed:
        return length == fixed[spec.section]
    if spec.section == "7.3.2":
        return length == 0
    if spec.section == "7.3.9":
        return length in (0x0B, 0x0C)
    if spec.section == "7.4.2":
        return length >= 9
    if spec.section == "7.4.4":
        return length >= 2 and (length - 2) % 23 == 0
    if spec.section == "7.4.14":
        return length >= 5 and (length - 5) % 12 == 0
    if spec.section == "7.4.15":
        return length >= 5
    if spec.section == "7.5.3":
        return length >= 2 and length == data[1] + 2
    if spec.section == "7.5.11":
        return 1 <= length <= 255
    return True


def _detail_matches(spec: CommandSpec, frame: ParsedFrame) -> bool:
    if spec.section in ("7.3.2", "7.4.16"):
        return True
    if spec.response_detail is not None and frame.detail != spec.response_detail:
        return False
    if spec.subcommand is not None:
        return len(frame.data) >= 2 and frame.data[1] == spec.subcommand
    return True


def _first_nack(frames: Iterable[ParsedFrame]) -> ParsedFrame | None:
    return next((frame for frame in frames if frame.kind == FrameKind.NACK), None)


def verify_command_response(
    spec: CommandSpec,
    received: bytes,
    profile: DeviceProfile,
    *,
    response_requested: bool = True,
) -> CommandVerification:
    """1コマンドの観測応答を仕様・設定と照合する。"""
    notes = list(response_context_notes(profile))
    if not received:
        if spec.response_pattern == ResponsePattern.NO_RESPONSE:
            return CommandVerification(VerificationResult.NO_RESPONSE_VERIFIED, (), tuple(notes))
        if spec.response_pattern == ResponsePattern.CONDITIONAL_ACK and not response_requested:
            return CommandVerification(VerificationResult.CONDITIONAL_NO_RESPONSE_VERIFIED, (), tuple(notes))
        notes.append("期待した応答を受信できませんでした")
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, (), tuple(notes))

    try:
        frames = split_frames(received)
    except ValueError as exc:
        notes.append(str(exc))
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, (), tuple(notes))

    nack_frame = _first_nack(frames)
    if nack_frame is not None:
        parsed_nack = parse_nack_frame(nack_frame.raw)
        notes.append("NACKは応答として解析済みだが、正常完了とは判定しません")
        return CommandVerification(VerificationResult.NACK_OBSERVED, frames, tuple(notes), parsed_nack)

    if spec.response_pattern == ResponsePattern.NO_RESPONSE:
        notes.append("応答なし仕様のコマンドで応答を受信しました")
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))

    if spec.response_pattern == ResponsePattern.MULTI_TAG_THEN_ACK:
        completion = frames[-1]
        expected_detail = spec.detail
        tag_frames = frames[:-1]
        if completion.kind != FrameKind.ACK or completion.detail != expected_detail or len(completion.data) != 5:
            notes.append("最終フレームが仕様どおりの完了ACKではありません")
            return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
        for frame in tag_frames:
            if frame.kind != FrameKind.TAG_DATA or frame.detail != expected_detail:
                notes.append("完了ACKより前に想定外のフレームがあります")
                return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
            address = interpret_address(frame, profile)
            if address.role == AddressRole.ANTENNA_NUMBER and address.value >= profile.antenna_capacity:
                notes.append(f"物理容量外のアンテナ番号です: {address.value}")
                return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
        notes.append(f"タグ応答={len(tag_frames)}件、完了ACK=1件")
        return CommandVerification(VerificationResult.MULTI_RESPONSE_VERIFIED, frames, tuple(notes))

    if len(frames) != 1 or frames[0].kind != FrameKind.ACK:
        notes.append("単一ACKを期待しましたが応答形態が一致しません")
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
    ack = frames[0]
    if not _detail_matches(spec, ack):
        notes.append("ACKの詳細コマンドが送信コマンドと一致しません")
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
    if not _length_matches(spec, ack.data):
        notes.append(f"ACKのDATA長が仕様と一致しません: {len(ack.data)}")
        return CommandVerification(VerificationResult.FAILED_NEEDS_ANALYSIS, frames, tuple(notes))
    return CommandVerification(VerificationResult.ACK_VERIFIED, frames, tuple(notes))
