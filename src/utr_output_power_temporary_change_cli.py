#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力を一時変更して復元する実機確認用CLI。

このCLIは、送信出力変更機能を main のInventory処理へ組み込む前に、
単独で実機確認するための安全確認用スクリプトです。

重要:
- 対象は ROMシリーズ名 USM02 / UTR-SUN02-4CH のみです。
- コマンドモード用パラメータだけを一時変更します。
- FLASHは変更しません。
- 終了時に、読み取り済みの元の送信出力へ復元します。
- Inventory処理は実行しません。
"""

from __future__ import annotations

import re
import sys

import serial
from serial.tools import list_ports

try:
    from src.utr_output_power_io import _read_current_output_power_setting, _send_output_power_frame
    from src.utr_output_power_temporary_change import (
        OutputPowerTemporaryChangePlans,
        build_output_power_temporary_change_plans,
        format_output_power_temporary_change_plans,
    )
    from src.utr_usb_sample import (
        ACK,
        COMMANDS,
        DETAIL_LOCATION,
        DETAIL_ROM,
        NACK,
        STX,
        ask_yes_no,
        close_serial_safely,
        communicate,
        format_rom_version_info,
        identify_model_key_from_rom,
        parse_baud_rate_input,
        parse_rom_version_response,
        print_nack_message,
        prompt_for_port_name,
    )
except ModuleNotFoundError:
    from utr_output_power_io import _read_current_output_power_setting, _send_output_power_frame
    from utr_output_power_temporary_change import (
        OutputPowerTemporaryChangePlans,
        build_output_power_temporary_change_plans,
        format_output_power_temporary_change_plans,
    )
    from utr_usb_sample import (
        ACK,
        COMMANDS,
        DETAIL_LOCATION,
        DETAIL_ROM,
        NACK,
        STX,
        ask_yes_no,
        close_serial_safely,
        communicate,
        format_rom_version_info,
        identify_model_key_from_rom,
        parse_baud_rate_input,
        parse_rom_version_response,
        print_nack_message,
        prompt_for_port_name,
    )

SUPPORTED_MODEL_KEY = "UTR-SUN02-4CH"


def _is_ack(response: bytes) -> bool:
    """ACKレスポンスかどうかを確認します。"""
    return bool(re.match(STX + b"." + ACK, response))


def _is_nack(response: bytes) -> bool:
    """NACKレスポンスかどうかを確認します。"""
    return bool(re.match(STX + b"." + NACK, response))


def _verify_supported_reader(ser: serial.Serial) -> None:
    """ROMバージョンを読み取り、対象機種か確認します。"""
    response = communicate(ser, COMMANDS["ROM_VERSION_CHECK"])
    if not _is_ack(response):
        if _is_nack(response):
            print_nack_message(response)
        else:
            print("Raw:", response.hex().upper())
        raise RuntimeError("ROMバージョン確認に失敗しました。")

    if bytes([response[DETAIL_LOCATION]]) != DETAIL_ROM:
        raise RuntimeError("ROMバージョン応答の詳細コマンドが一致しません。")

    rom_info = parse_rom_version_response(response)
    identified_model_key = identify_model_key_from_rom(rom_info)
    for line in format_rom_version_info(rom_info, identified_model_key=identified_model_key):
        print(line)

    if identified_model_key != SUPPORTED_MODEL_KEY:
        raise RuntimeError(
            "このCLIは UTR-SUN02-4CH / USM02 専用です。"
            f" 現在の判定: {identified_model_key or '不明'}"
        )


def _set_command_mode(ser: serial.Serial) -> None:
    """リーダライタをコマンドモードへ切り替えます。"""
    response = communicate(ser, COMMANDS["COMMAND_MODE_SET"])
    if _is_ack(response):
        print("コマンドモードに切り替えました。")
        return

    if _is_nack(response):
        print_nack_message(response)
        raise RuntimeError("コマンドモード切替でNACKを受信しました。")

    print("Raw:", response.hex().upper())
    raise RuntimeError("コマンドモード切替でACK/NACKがありません。")


def run_temporary_output_power_change(ser: serial.Serial) -> None:
    """送信出力を一時変更し、最後に元へ戻します。"""
    current_setting = _read_current_output_power_setting(ser)

    print("")
    print("変更後の送信出力値を入力してください。")
    print("例: 20.0 / 24.0")
    print("変更しない場合は Enter または q を入力してください。")
    user_input = input("送信出力[dBm]: ").strip()

    plans = build_output_power_temporary_change_plans(current_setting, user_input)
    if plans is None:
        print("送信出力は変更しません。")
        return

    for line in format_output_power_temporary_change_plans(plans):
        print(line)

    if not ask_yes_no("この内容で一時変更しますか？ [y/N]: ", default=False):
        print("送信出力は変更しません。")
        return

    changed = False
    try:
        _send_output_power_frame(ser, plans.change_plan.command_frame, "送信出力の一時変更")
        changed = True
        _read_current_output_power_setting(ser)
        print("")
        input("確認が終わったら Enter を押してください。元の送信出力へ復元します。")
    finally:
        if changed:
            _restore_output_power_setting(ser, plans)


def _restore_output_power_setting(ser: serial.Serial, plans: OutputPowerTemporaryChangePlans) -> None:
    """送信出力を元の値へ復元します。"""
    try:
        _send_output_power_frame(ser, plans.restore_plan.command_frame, "送信出力の復元")
        _read_current_output_power_setting(ser)
    except Exception as exc:
        print("")
        print("送信出力の復元に失敗しました。")
        print("UTRRWManagerまたは再実行時の読み取りで、機器側の現在設定を確認してください。")
        print(f"復元エラー: {exc}")
        raise


def main() -> None:
    """CLIのエントリポイント。"""
    print("UTR-SUN02-4CH 送信出力一時変更CLIを開始します。")
    print("FLASHは変更しません。Inventoryは実行しません。")

    ports = list_ports.comports()
    if not ports:
        print("利用可能なCOMポートが見つかりませんでした。")
        sys.exit(1)

    port_name = prompt_for_port_name(ports)
    baud_rate_str = input("ボーレートを入力してください（例: 19200, 115200, 未入力なら115200）: ")
    baud_rate = parse_baud_rate_input(baud_rate_str)

    ser: serial.Serial | None = None
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=baud_rate,
            timeout=0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"接続成功: {port_name} @ {baud_rate}bps")

        _verify_supported_reader(ser)
        _set_command_mode(ser)
        run_temporary_output_power_change(ser)
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。")
    except Exception as exc:
        print("")
        print("送信出力一時変更CLIでエラーが発生しました。")
        print(f"エラー内容: {exc}")
        sys.exit(1)
    finally:
        if ser is not None:
            close_serial_safely(ser)


if __name__ == "__main__":
    main()
