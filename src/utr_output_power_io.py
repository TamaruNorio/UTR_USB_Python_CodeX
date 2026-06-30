#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力設定の実機I/O共通処理。

このモジュールは、送信出力の読み取りと、送信出力設定フレームの送信確認だけを扱います。

重要:
- FLASHは変更しません。
- フレームの生成は行いません。
- 送信するフレームは呼び出し元で作成済みのものだけです。
- ACK/NACK判定と表示を共通化し、CLIファイルへ共通ヘルパーを置かないための分離です。
"""

from __future__ import annotations

import re
from typing import Any

import serial

try:
    from src.utr_reader_settings import format_output_power_setting, parse_output_power_setting_response
    from src.utr_usb_sample import ACK, COMMANDS, NACK, STX, communicate, print_nack_message
except ModuleNotFoundError:
    from utr_reader_settings import format_output_power_setting, parse_output_power_setting_response
    from utr_usb_sample import ACK, COMMANDS, NACK, STX, communicate, print_nack_message


def _is_ack(response: bytes) -> bool:
    """ACKレスポンスかどうかを確認します。"""
    return bool(re.match(STX + b"." + ACK, response))


def _is_nack(response: bytes) -> bool:
    """NACKレスポンスかどうかを確認します。"""
    return bool(re.match(STX + b"." + NACK, response))


def _read_current_output_power_setting(ser: serial.Serial) -> dict[str, Any]:
    """現在の送信出力設定を読み取り、画面表示用に整形して出力します。"""
    response = communicate(ser, COMMANDS["UHF_READ_OUTPUT_POWER"])
    if _is_ack(response):
        parsed = parse_output_power_setting_response(response)
        print("")
        print("=== 現在の送信出力設定 ===")
        for line in format_output_power_setting(parsed):
            print(line)
        return parsed

    if _is_nack(response):
        print_nack_message(response)
        raise RuntimeError("送信出力設定の読み取りでNACKを受信しました。")

    print("Raw:", response.hex().upper())
    raise RuntimeError("送信出力設定の読み取りでACK/NACKがありません。")


def _send_output_power_frame(ser: serial.Serial, frame: bytes, label: str) -> None:
    """送信出力設定フレームを送信し、ACK/NACKを確認します。"""
    print("")
    print(f"{label}を送信します。")
    print("FLASHは変更しません。")
    print("送信フレーム:", frame.hex(" ").upper())

    response = communicate(ser, frame)
    if _is_ack(response):
        print(f"{label}がACKで完了しました。")
        return

    if _is_nack(response):
        print_nack_message(response)
        raise RuntimeError(f"{label}でNACKを受信しました。")

    print("Raw:", response.hex().upper())
    raise RuntimeError(f"{label}でACK/NACKがありません。")
