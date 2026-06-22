#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力を一時変更してInventoryする実機確認用エントリポイント。

このスクリプトは、既存の `utr_usb_sample.py` 本体を大きく書き換えずに、
送信出力一時変更を含むInventoryフローを実機確認するための入口です。

動作概要:
- USBシリアル接続します。
- ROMバージョンを読み取り、機種を確認します。
- コマンドモードへ切り替えます。
- UTR-SUN02-4CH / USM02 かつ現在設定が読める場合、送信出力の一時変更を提案します。
- Inventoryを実行します。
- 終了時に送信出力を元に戻します。
- 既存のアンテナ設定復元と結果保存も実行します。

注意:
- FLASHは変更しません。
- 送信出力はコマンドモード用パラメータだけを一時変更します。
- 8CHアンテナ制御は実装しません。
"""

from __future__ import annotations

import re
import sys
import time
from typing import Any, Optional

import serial
from serial.tools import list_ports

try:
    from src.utr_output_power_inventory_integration import (
        evaluate_output_power_temporary_change_availability,
        format_output_power_temporary_change_offer,
    )
    from src.utr_output_power_temporary_change import (
        OutputPowerTemporaryChangePlans,
        build_output_power_temporary_change_plans,
        format_output_power_temporary_change_plans,
    )
    from src.utr_output_power_temporary_change_cli import (
        _read_current_output_power_setting,
        _send_output_power_frame,
    )
    from src.utr_privacy import get_or_create_masked_pc_uii_id
    from src.utr_usb_sample import (
        ACK,
        COMMANDS,
        DETAIL_LOCATION,
        DETAIL_ROM,
        NACK,
        STX,
        AntennaCheckTarget,
        AntennaSwitchingSetting,
        InventoryAntennaSelection,
        ask_yes_no,
        communicate,
        finish_inventory_session,
        format_pc_uii_for_display,
        format_rom_version_info,
        identify_model_key_from_rom,
        parse_baud_rate_input,
        parse_inventory_param_response,
        parse_rom_version_response,
        play_buzzer_for_inventory_result,
        print_nack_message,
        prompt_for_port_name,
        read_and_print_pre_inventory_reader_settings,
        received_data_contains_nack,
        received_data_parse,
        run_optional_antenna_check,
        should_stop_inventory_repeat,
        write_command_mode_antenna_setting,
    )
    from src.utr_inventory import format_inventory_param_response
except ModuleNotFoundError:
    from utr_output_power_inventory_integration import (
        evaluate_output_power_temporary_change_availability,
        format_output_power_temporary_change_offer,
    )
    from utr_output_power_temporary_change import (
        OutputPowerTemporaryChangePlans,
        build_output_power_temporary_change_plans,
        format_output_power_temporary_change_plans,
    )
    from utr_output_power_temporary_change_cli import (
        _read_current_output_power_setting,
        _send_output_power_frame,
    )
    from utr_privacy import get_or_create_masked_pc_uii_id
    from utr_usb_sample import (
        ACK,
        COMMANDS,
        DETAIL_LOCATION,
        DETAIL_ROM,
        NACK,
        STX,
        AntennaCheckTarget,
        AntennaSwitchingSetting,
        InventoryAntennaSelection,
        ask_yes_no,
        communicate,
        finish_inventory_session,
        format_pc_uii_for_display,
        format_rom_version_info,
        identify_model_key_from_rom,
        parse_baud_rate_input,
        parse_inventory_param_response,
        parse_rom_version_response,
        play_buzzer_for_inventory_result,
        print_nack_message,
        prompt_for_port_name,
        read_and_print_pre_inventory_reader_settings,
        received_data_contains_nack,
        received_data_parse,
        run_optional_antenna_check,
        should_stop_inventory_repeat,
        write_command_mode_antenna_setting,
    )
    from utr_inventory import format_inventory_param_response


def _is_ack(response: bytes) -> bool:
    return bool(re.match(STX + b"." + ACK, response))


def _is_nack(response: bytes) -> bool:
    return bool(re.match(STX + b"." + NACK, response))


def _verify_usb_and_read_model_key(ser: serial.Serial) -> tuple[object | None, str | None]:
    """ROMバージョンを読み取り、仕様書照合機種キーを返します。"""
    result = communicate(ser, COMMANDS["ROM_VERSION_CHECK"])
    if _is_ack(result):
        if bytes([result[DETAIL_LOCATION]]) == DETAIL_ROM:
            print("USB通信: OK（ROMバージョン ACK 受信）")
            rom_info = parse_rom_version_response(result)
            identified_model_key = identify_model_key_from_rom(rom_info)
            for line in format_rom_version_info(rom_info, identified_model_key=identified_model_key):
                print(line)
            return rom_info, identified_model_key
        raise RuntimeError("ROMバージョン応答の詳細コマンドが一致しません。")

    if _is_nack(result):
        print_nack_message(result)
        raise RuntimeError("ROMバージョン確認でNACKを受信しました。")

    print("Raw:", result.hex().upper())
    raise RuntimeError("USB通信: NG（ACK/NACK なし）")


def _set_command_mode(ser: serial.Serial) -> None:
    """コマンドモードへ切り替えます。"""
    result = communicate(ser, COMMANDS["COMMAND_MODE_SET"])
    if _is_ack(result):
        print("コマンドモードに切り替えました。")
        return

    if _is_nack(result):
        print_nack_message(result)
        raise RuntimeError("コマンドモード切替でNACKを受信しました。")

    print("Raw:", result.hex().upper())
    raise RuntimeError("コマンドモード切替に失敗しました。")


def _create_output_power_restore_state() -> dict[str, Any]:
    """送信出力一時変更の復元状態を保持します。

    plans:
        変更用フレームと復元用フレームのセットです。
    restore_required:
        変更送信を試みたため、異常終了時に復元対象とみなす状態です。
        ACK後の読み戻しで例外が発生しても復元できるようにします。
    restore_done:
        finallyで二重復元しないためのフラグです。
    """
    return {
        "plans": None,
        "restore_required": False,
        "restore_done": False,
    }


def _offer_temporary_output_power_change(
    ser: serial.Serial,
    identified_model_key: str | None,
    restore_state: dict[str, Any] | None = None,
) -> OutputPowerTemporaryChangePlans | None:
    """Inventory前に送信出力一時変更を提案し、変更した場合は復元計画を返します。"""
    current_setting = _read_current_output_power_setting(ser)
    availability = evaluate_output_power_temporary_change_availability(
        identified_model_key,
        current_setting,
    )

    print("")
    print("=== Inventory前の送信出力一時変更 ===")
    for line in format_output_power_temporary_change_offer(availability):
        print(line)

    if not availability.can_offer:
        return None

    if not ask_yes_no("送信出力をInventory中だけ一時変更しますか？ [y/N]: ", default=False):
        print("送信出力は変更しません。")
        return None

    print("変更後の送信出力値を入力してください。例: 12.0 / 20.0 / 24.0")
    user_input = input("送信出力[dBm]: ").strip()
    plans = build_output_power_temporary_change_plans(current_setting, user_input)
    if plans is None:
        print("送信出力は変更しません。")
        return None

    for line in format_output_power_temporary_change_plans(plans):
        print(line)

    if not ask_yes_no("この内容で一時変更してInventoryへ進みますか？ [y/N]: ", default=False):
        print("送信出力は変更しません。")
        return None

    if restore_state is not None:
        restore_state["plans"] = plans
        restore_state["restore_required"] = True

    _send_output_power_frame(ser, plans.change_plan.command_frame, "送信出力の一時変更")
    _read_current_output_power_setting(ser)
    return plans


def _restore_temporary_output_power(
    ser: serial.Serial,
    plans: OutputPowerTemporaryChangePlans | None,
    restore_state: dict[str, Any] | None = None,
) -> None:
    """一時変更した送信出力を元に戻します。"""
    effective_plans = plans
    if restore_state is not None:
        if restore_state.get("restore_done"):
            return
        if not restore_state.get("restore_required"):
            return
        effective_plans = effective_plans or restore_state.get("plans")

    if effective_plans is None:
        return

    try:
        _send_output_power_frame(ser, effective_plans.restore_plan.command_frame, "送信出力の復元")
        _read_current_output_power_setting(ser)
    except Exception as exc:
        print("")
        print("送信出力の復元に失敗しました。")
        print("UTRRWManagerまたは再実行時の読み取りで、機器側の現在設定を確認してください。")
        print(f"復元エラー: {exc}")
    finally:
        if restore_state is not None:
            restore_state["restore_done"] = True


def _read_inventory_parameters(ser: serial.Serial) -> None:
    """Inventoryパラメータを読み取り、表示します。"""
    result = communicate(ser, COMMANDS["UHF_GET_INVENTORY_PARAM"])
    if _is_ack(result):
        print("UHF_GET_INVENTORY_PARAM が正常に実行されました")
    elif _is_nack(result):
        print_nack_message(result)
        raise RuntimeError("UHF_GET_INVENTORY_PARAMでNACKを受信しました。")
    else:
        print("UHF_GET_INVENTORY_PARAM 実行エラー")
        print(result.hex().upper())
        raise RuntimeError("UHF_GET_INVENTORY_PARAMでACK/NACKがありません。")

    print("UHF_GET_INVENTORY_PARAM response:", result.hex().upper())
    inventory_param = parse_inventory_param_response(result)
    for line in format_inventory_param_response(inventory_param):
        print(line)
    print("UHF_SET_INVENTORY_PARAM は自動送信しません。設定変更は行いません。")


def _run_inventory_loop(
    ser: serial.Serial,
    antenna_selection: Optional[InventoryAntennaSelection],
) -> tuple[int, float, int, dict, dict]:
    """既存サンプルと同じ考え方でInventoryループを実行します。"""
    total_read_time = 0.0
    total_read_count = 0
    total_iterations = 0
    pc_uii_count_dict: dict = {}
    inventory_result_item_dict: dict = {}
    export_mask_map: dict[str, str] = {}

    buzzer_enabled = ask_yes_no("読み取り結果をブザーで通知しますか？ [y/N]: ", default=False)
    mask_pc_uii_display = ask_yes_no("PC+UIIを画面表示でマスクしますか？ [y/N]: ", default=False)
    mask_pc_uii_export = ask_yes_no("結果ファイルでもPC+UIIをマスクしますか？ [y/N]: ", default=False)
    if mask_pc_uii_display:
        print("PC+UIIは画面表示で省略します。")
    if mask_pc_uii_export:
        print("結果ファイルのPC+UIIは MASKED_PC_UII_001 のような仮名IDで保存します。")
    else:
        print("結果ファイルには実PC+UIIを保持します。共有時は必ずマスクしてください。")

    while True:
        try:
            repeat_count_str = input("繰り返す回数を入力してください（1〜100、終了は'q'）: ").strip()
            if repeat_count_str.lower() == "q":
                break
            repeat_count = int(repeat_count_str)
            if not (1 <= repeat_count <= 100):
                raise ValueError("1から100の範囲で入力してください")
        except ValueError as exc:
            print(f"入力エラー: {exc}。再度入力してください。")
            continue

        inventory_targets: list[AntennaCheckTarget | None] = [None]
        current_antenna_setting: Optional[AntennaSwitchingSetting] = None
        if antenna_selection is not None and antenna_selection.selected_targets:
            inventory_targets = list(antenna_selection.selected_targets)
            current_antenna_setting = antenna_selection.restore_setting

        total_iterations += repeat_count * len(inventory_targets)
        start_time = time.time()
        stop_current_request = False

        for _ in range(repeat_count):
            for inventory_target in inventory_targets:
                if inventory_target is not None:
                    print("")
                    print(f"--- Inventory対象: {inventory_target.label}（{inventory_target.description}） ---")
                    if current_antenna_setting is None:
                        print("現在のアンテナ設定が不明なため、このアンテナのInventoryをスキップします。")
                        continue
                    updated_setting = write_command_mode_antenna_setting(
                        ser=ser,
                        current_setting=current_antenna_setting,
                        target=inventory_target,
                    )
                    if updated_setting is None:
                        print(f"{inventory_target.label}への切替に失敗したため、このアンテナのInventoryをスキップします。")
                        continue
                    current_antenna_setting = updated_setting

                result = communicate(ser, COMMANDS["UHF_INVENTORY"])
                if result:
                    has_nack = received_data_contains_nack(result)
                    pc_uii_list, rssi_list, expected_count, read_channel = received_data_parse(result)
                    if expected_count is not None:
                        print(f"読み取り完了レスポンス枚数: {expected_count} 枚")
                    if read_channel is not None:
                        print(f"読み取りチャンネル: {read_channel} ch")

                    for pc_uii, rssi_value in zip(pc_uii_list, rssi_list):
                        pc_uii_hex = pc_uii.hex().upper()
                        export_pc_uii = (
                            get_or_create_masked_pc_uii_id(pc_uii_hex, export_mask_map)
                            if mask_pc_uii_export
                            else pc_uii_hex
                        )
                        print(f"PC+UII: {format_pc_uii_for_display(pc_uii_hex, mask=mask_pc_uii_display)}")
                        print(f"RSSI: {rssi_value:.1f} dBm")
                        pc_uii_count_dict[export_pc_uii] = pc_uii_count_dict.get(export_pc_uii, 0) + 1
                        antenna_number = inventory_target.number if inventory_target is not None else None
                        antenna_label = inventory_target.label if inventory_target is not None else None
                        antenna_description = inventory_target.description if inventory_target is not None else None
                        item_key = (export_pc_uii, antenna_number, antenna_label, antenna_description)
                        if item_key not in inventory_result_item_dict:
                            inventory_result_item_dict[item_key] = {
                                "antenna_number": antenna_number,
                                "antenna_label": antenna_label,
                                "antenna_description": antenna_description,
                                "pc_uii": export_pc_uii,
                                "read_count": 0,
                            }
                        inventory_result_item_dict[item_key]["read_count"] += 1

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
                else:
                    print("インベントリ応答がありませんでした。")
                    if buzzer_enabled:
                        play_buzzer_for_inventory_result(ser, has_tag=False, has_nack=False)
            if stop_current_request:
                break

        total_read_time += time.time() - start_time
        print(f"現在の合計読み取り時間: {total_read_time:.2f} 秒")
        print(f"現在の合計読み取り枚数: {total_read_count} 枚")

    return total_iterations, total_read_time, total_read_count, pc_uii_count_dict, inventory_result_item_dict


def main() -> None:
    """送信出力一時変更つきInventoryのエントリポイント。"""
    print("UTR（USBモデル）に接続します。")
    print("送信出力一時変更つきInventoryフローです。FLASHは変更しません。")

    ports = list_ports.comports()
    if not ports:
        print("利用可能なCOMポートが見つかりませんでした。")
        sys.exit(1)

    port_name = prompt_for_port_name(ports)
    baud_rate_str = input("ボーレートを入力してください（例: 19200, 115200, 未入力なら115200）: ")
    baud_rate = parse_baud_rate_input(baud_rate_str)

    ser: serial.Serial | None = None
    antenna_selection: Optional[InventoryAntennaSelection] = None
    output_power_plans: OutputPowerTemporaryChangePlans | None = None
    output_power_restore_state = _create_output_power_restore_state()
    total_iterations = 0
    total_read_time = 0.0
    total_read_count = 0
    pc_uii_count_dict: dict = {}
    inventory_result_item_dict: dict = {}

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

        rom_info, identified_model_key = _verify_usb_and_read_model_key(ser)
        _set_command_mode(ser)
        output_power_plans = _offer_temporary_output_power_change(
            ser,
            identified_model_key,
            restore_state=output_power_restore_state,
        )

        read_and_print_pre_inventory_reader_settings(ser)
        _read_inventory_parameters(ser)
        antenna_selection = run_optional_antenna_check(ser, rom_info=rom_info)

        (
            total_iterations,
            total_read_time,
            total_read_count,
            pc_uii_count_dict,
            inventory_result_item_dict,
        ) = _run_inventory_loop(ser, antenna_selection)
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了処理を行います。")
    except Exception as exc:
        print("")
        print("送信出力一時変更つきInventory処理中にエラーが発生しました。終了処理を行います。")
        print(f"エラー内容: {exc}")
    finally:
        if ser is not None:
            _restore_temporary_output_power(
                ser,
                output_power_plans,
                restore_state=output_power_restore_state,
            )
            finish_inventory_session(
                ser,
                antenna_selection,
                total_iterations,
                total_read_time,
                total_read_count,
                pc_uii_count_dict,
                inventory_result_item_dict,
            )


if __name__ == "__main__":
    main()
