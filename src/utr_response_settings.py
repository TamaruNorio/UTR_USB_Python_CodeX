#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""応答の件数・順序・2バイト目へ影響する設定値の解析。"""

from __future__ import annotations

from dataclasses import dataclass

from src.utr_response_v117 import FrameKind, parse_frame


@dataclass(frozen=True)
class EpcUiiResponseSettings:
    parameter_kind: int
    epc_buffering_enabled: bool
    read_cycle_completion_enabled: bool
    antenna_switch_completion_enabled: bool
    carrier_detect_response_enabled: bool


def parse_epc_uii_response_settings(frame: bytes) -> EpcUiiResponseSettings:
    """7.4.9の4バイトDATAを解析する。"""
    parsed = parse_frame(frame)
    if parsed.kind != FrameKind.ACK:
        raise ValueError("EPC(UII)関連パラメータ応答がACKではありません")
    if len(parsed.data) != 4 or parsed.data[:2] != b"\x43\x05":
        raise ValueError("EPC(UII)関連パラメータ応答の識別子またはDATA長が不正です")
    flags = parsed.data[3]
    if flags & 0xF0:
        raise ValueError("EPC(UII)関連パラメータの予約ビットが0ではありません")
    return EpcUiiResponseSettings(
        parameter_kind=parsed.data[2],
        epc_buffering_enabled=bool(flags & 0x01),
        read_cycle_completion_enabled=bool(flags & 0x02),
        antenna_switch_completion_enabled=bool(flags & 0x04),
        carrier_detect_response_enabled=bool(flags & 0x08),
    )
