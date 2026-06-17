#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02-8CH向け 単一アンテナInventory確認CLI。

このCLIは、8CH機でInventoryへ進むための最初の実機確認入口です。

実行すること:
- USBシリアル接続
- ROMバージョン読み取り
- 8CH機種判定
- コマンドモード切替
- ANT1〜ANT8のUHF_CheckAntenna
- 接続OKアンテナから1つだけ選択
- 選択したアンテナ情報を付けてUHF_INVENTORYを実行

現段階で実行しないこと:
- アンテナ切替設定の書き込み
- 複数アンテナ順次切替
- 送信出力変更
- FLASH書き込み
- UHF_SET_INVENTORY_PARAM送信

注意:
- UTR-SUN02-8CHのANT1は使用アンテナ番号00hです。
- まずANT1だけでInventory疎通を確認します。
- ANT2以降の実切替は次段階で実装します。
"""

from __future__ import annotations

import sys
import time

import serial
from serial.tools import list_ports

try:
    from src.utr_8ch import (
        build_8ch_inventory_targets,
        format_8ch_inventory_candidate,
        is_8ch_model_key,
        parse_8ch_inventory_selection_input,
    )
    from src.utr_usb_inventory_with_output_power import (
        _is_nack,
        _read_inventory_parameters,
        _set_command_mode,
        _verify_usb_and_read_model_key,
    )
    from src.utr_usb_sample import (
        COMMANDS,
        ask_yes_no,
        check_and_print_antennas,
        close_serial_safely,
        communicate,
        format_pc_uii_for_display,
        get_model_profile,
        parse_baud_rate_input,
        play_buzzer_for_inventory_result,
        print_nack_message,
        prompt_for_port_name,
        read_and_print_pre_inventory_reader_settings,
        received_data_contains_nack,
        received_data_parse,
        should_stop_inventory_repeat,
    )
except ModuleNotFoundError:
    from utr_8ch import (
        build_8ch_inventory_targets,
        format_8ch_inventory_candidate,
        is_8ch_model_key,
        parse_8ch_inventory_selection_input,
    )
    from utr_usb_inventory_with_output_power import (
        _is_nack,
        _read_inventory_parameters,
        _set_command_mode,
        _verify_usb_and_read_model_key,
    )
    from utr_usb_sample import (
        COMMANDS,
        ask_yes_no,
        check_and_print_antennas,
        close_serial_safely,
        communicate,
        format_pc_uii_for_display,
        get_model_profile,
        parse_baud_rate_input,
        play_buzzer_for_inventory_result,
        print_nack_message,
        prompt_for_port_name,
        read_and_print_pre_inventory_reader_settings,
        received_data_contains_nack,
        received_data_parse,
        should_stop_inventory_repeat,
    )


def _select_single_8ch_inventory_target(connected_targets):
    """接続OKアンテナから、単一の8CH Inventory対象を選択します。"""
    available_targets = build_8ch_inventory_targets(connected_targets)
    if not available_targets:
        print("8CH Inventoryに使用できる接続OKアンテナがありません。")
        return None

    print("")
    print("=== 8CH単一アンテナInventory対象選択 ===")
    for target in available_targets:
        print(format_8ch_inventory_candidate(target))
    print("現段階では1つだけ選択してください。例: 1")
    print("アンテナ切替設定の書き込みはまだ行いません。")

    while True:
        value = input("8CH Inventoryに使用するANT番号を1つ入力してください（終了は'q'）: ").strip()
        try:
            selected_targets = parse_8ch_inventory_selection_input(available_targets, value)
        except ValueError as exc:
            print(f"入力エラー: {exc}")
            continue

        if selected_targets is None:
            print("8CH Inventory対象選択を中止しました。")
            return None
        if len(selected_targets) != 1:
            print("現段階では1つだけ選択してください。複数アンテナ順次切替は次段階で実装します。")
            continue

        target = selected_targets[0]
        print(f"選択: {target.label} / 使用アンテナ番号 {target.usage_antenna_number_hex}")
        return target


def _run_single_antenna_inventory_loop(ser: serial.Serial, target) -> tuple[int, float, int]:
    """選択済み8CHアンテナ情報を表示しながらInventoryを実行します。"""
    total_iterations = 0
    total_read_time = 0.0
    total_read_count = 0

    buzzer_enabled = ask_yes_no("読み取り結果をブザーで通知しますか？ [y/N]: ", default=False)
    mask_pc_uii_display = ask_yes_no("PC+UIIを画面表示でマスクしますか？ [y/N]: ", default=False)

    print("")
    print("=== 8CH単一アンテナInventory ===")
    print(f"対象アンテナ: {target.label}")
    print(f"使用アンテナ番号: {target.usage_antenna_number_hex}")
    print("現段階ではアンテナ切替設定の書き込みは行いません。")
    print("まず現在の選択アンテナ状態でUHF_INVENTORYの疎通を確認します。")

    while True:
        repeat_count_str = input("繰り返す回数を入力してください（1〜100、終了は'q'）: ").strip()
        if repeat_count_str.lower() == "q":
            break
        try:
            repeat_count = int(repeat_count_str)
            if not (1 <= repeat_count <= 100):
                raise ValueError("1から100の範囲で入力してください")
        except ValueError as exc:
            print(f"入力エラー: {exc}。再度入力してください。")
            continue

        total_iterations += repeat_count
        start_time = time.time()
        stop_current_request = False

        for index in range(repeat_count):
            print("")
            print(f"--- {target.label} Inventory {index + 1}/{repeat_count} ---")
            result = communicate(ser, COMMANDS["UHF_INVENTORY"])
            if not result:
                print("インベントリ応答がありませんでした。")
                if buzzer_enabled:
                    play_buzzer_for_inventory_result(ser, has_tag=False, has_nack=False)
                continue

            if _is_nack(result):
                print_nack_message(result)

            has_nack = received_data_contains_nack(result)
            pc_uii_list, rssi_list, expected_count, read_channel = received_data_parse(result)
            if expected_count is not None:
                print(f"読み取り完了レスポンス枚数: {expected_count} 枚")
            if read_channel is not None:
                print(f"読み取りチャンネル: {read_channel} ch")
            print(f"確認対象アンテナ: {target.label} / 使用アンテナ番号 {target.usage_antenna_number_hex}")

            for pc_uii, rssi_value in zip(pc_uii_list, rssi_list):
                pc_uii_hex = pc_uii.hex().upper()
                print(f"PC+UII: {format_pc_uii_for_display(pc_uii_hex, mask=mask_pc_uii_display)}")
                print(f"RSSI: {rssi_value:.1f} dBm")

            total_read_count += len(pc_uii_list)
            if buzzer_enabled:
                play_buzzer_for_inventory_result(
                    ser,
                    has_tag=len(pc_uii_list) > 0,
                    has_nack=has_nack,
                )
            if should_stop_inventory_repeat(has_nack):
                print("NACK応答を受信したため、指定回数の残り読み取りを中断します。")
                stop_current_request = True
                break

        total_read_time += time.time() - start_time
        print(f"現在の合計読み取り時間: {total_read_time:.2f} 秒")
        print(f"現在の合計読み取り枚数: {total_read_count} 枚")

        if stop_current_request:
            continue

    return total_iterations, total_read_time, total_read_count


def main() -> None:
    """UTR-SUN02-8CHの単一アンテナInventory確認を行います。"""
    print("UTR-SUN02-8CH 単一アンテナInventory確認を開始します。")
    print("FLASH、送信出力、Inventoryパラメータは変更しません。")
    print("現段階ではアンテナ切替設定の書き込みも行いません。")

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
            print("8CH機ではないため、このCLIではInventoryを実行しません。")
            return

        _set_command_mode(ser)
        read_and_print_pre_inventory_reader_settings(ser)
        _read_inventory_parameters(ser)

        profile = get_model_profile(identified_model_key)
        connected_targets = check_and_print_antennas(ser, profile)
        target = _select_single_8ch_inventory_target(connected_targets)
        if target is None:
            return

        total_iterations, total_read_time, total_read_count = _run_single_antenna_inventory_loop(ser, target)

        print("")
        print("=== 8CH単一アンテナInventory結果まとめ ===")
        print(f"対象アンテナ: {target.label}")
        print(f"使用アンテナ番号: {target.usage_antenna_number_hex}")
        print(f"Inventory実行回数: {total_iterations}")
        print(f"合計読み取り時間: {total_read_time:.2f} 秒")
        print(f"合計読み取り枚数: {total_read_count} 枚")
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了します。")
    except Exception as exc:
        print("")
        print("8CH単一アンテナInventory確認中にエラーが発生しました。")
        print(f"エラー内容: {exc}")
    finally:
        if ser is not None:
            close_serial_safely(ser)


if __name__ == "__main__":
    main()
