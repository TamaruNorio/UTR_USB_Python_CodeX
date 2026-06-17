#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向けの読み取り専用アンテナ診断CLI。

このCLIは、8CH実機の初期確認用です。

実行内容:
- USBシリアル接続
- ROMバージョン読み取り
- 8CH機種判定
- コマンドモード切替
- ANT1〜ANT8のUHF_CheckAntenna実行

行わないこと:
- アンテナ切替設定の書き込み
- 送信出力変更
- Inventory
- FLASH書き込み
- UHF_SET_INVENTORY_PARAM送信
"""

from __future__ import annotations

import sys

import serial
from serial.tools import list_ports

try:
    from src.utr_8ch import format_8ch_diagnostic_notes, is_8ch_model_key
    from src.utr_usb_inventory_with_output_power import _set_command_mode, _verify_usb_and_read_model_key
    from src.utr_usb_sample import (
        check_and_print_antennas,
        close_serial_safely,
        get_model_profile,
        parse_baud_rate_input,
        prompt_for_port_name,
    )
except ModuleNotFoundError:
    from utr_8ch import format_8ch_diagnostic_notes, is_8ch_model_key
    from utr_usb_inventory_with_output_power import _set_command_mode, _verify_usb_and_read_model_key
    from utr_usb_sample import (
        check_and_print_antennas,
        close_serial_safely,
        get_model_profile,
        parse_baud_rate_input,
        prompt_for_port_name,
    )


def main() -> None:
    """8CH機のアンテナ接続状態を読み取り専用で確認します。"""
    print("UTR-SUN02 8CH機の読み取り専用アンテナ診断を開始します。")
    print("アンテナ切替設定、送信出力、FLASH、Inventoryパラメータは変更しません。")

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

        _rom_info, identified_model_key = _verify_usb_and_read_model_key(ser)
        if not is_8ch_model_key(identified_model_key):
            for line in format_8ch_diagnostic_notes(identified_model_key):
                print(line)
            return

        _set_command_mode(ser)

        print("")
        print("=== 8CHアンテナ診断（読み取り専用） ===")
        for line in format_8ch_diagnostic_notes(identified_model_key):
            print(line)

        profile = get_model_profile(identified_model_key)
        connected_targets = check_and_print_antennas(ser, profile)
        connected_text = ", ".join(target.label for target in connected_targets) if connected_targets else "なし"

        print("")
        print("=== 8CH診断結果まとめ ===")
        print(f"接続OKアンテナ: {connected_text}")
        print("次の段階で、この結果をもとに8CH用Inventory切替処理を実装します。")
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了します。")
    except Exception as exc:
        print("")
        print("8CHアンテナ診断中にエラーが発生しました。")
        print(f"エラー内容: {exc}")
    finally:
        if ser is not None:
            close_serial_safely(ser)


if __name__ == "__main__":
    main()
