#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02-8CH向け 複数アンテナ順次Inventory確認CLI。

このCLIは、UTR-SUN02-8CH / USM08 で接続OKだったアンテナをユーザーが選択し、
選択順に「使用アンテナ番号設定」→「UHF_Inventory」を実行するための実機確認入口です。

実行すること:
- USBシリアル接続
- ROMバージョン読み取り
- UTR-SUN02-8CH / USM08 判定
- コマンドモード切替
- Inventory前のリーダ設定表示
- UHF_GET_INVENTORY_PARAM表示
- ANT1〜ANT8のUHF_CheckAntenna
- 接続OKアンテナから 1 / 1,3 / all / q で選択
- 選択した全ANTの使用アンテナ番号設定フレームを事前表示
- 最初に1回だけ確認し、選択順に使用アンテナ番号設定を送信
- ACKならそのANTでInventory
- NACKまたは応答なしなら、そのANTはスキップ
- ANTごとの読み取り枚数を集計
- 必要に応じて、ANT別サマリをCSV/JSONへ保存

実行しないこと:
- FLASH書き込み
- 送信出力変更
- 周波数変更
- UHF_SET_INVENTORY_PARAM送信
- 接続エラーANTへの強制Inventory
- 8CH設定の永続保存
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import serial
from serial.tools import list_ports

try:
    from src.utr_8ch import (
        build_8ch_inventory_targets,
        build_sun02_8ch_usage_antenna_command_dry_run,
        format_8ch_inventory_candidate,
        format_8ch_usage_antenna_command_dry_run,
        parse_8ch_inventory_selection_input,
    )
    from src.utr_usb_inventory_with_output_power import (
        _is_ack,
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
        build_sun02_8ch_usage_antenna_command_dry_run,
        format_8ch_inventory_candidate,
        format_8ch_usage_antenna_command_dry_run,
        parse_8ch_inventory_selection_input,
    )
    from utr_usb_inventory_with_output_power import (
        _is_ack,
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


SUMMARY_CSV_FILENAME = "8ch_sequential_inventory_summary.csv"
SUMMARY_JSON_FILENAME = "8ch_sequential_inventory_summary.json"
SUMMARY_TARGET_MODEL = "UTR-SUN02-8CH"
SUMMARY_CSV_FIELDNAMES = [
    "saved_at",
    "target_model",
    "selected_order",
    "total_inventory_attempts",
    "total_read_time_seconds",
    "total_read_count",
    "last_used_antenna_label",
    "restore_requested",
    "restore_target_label",
    "restore_success",
    "restore_message",
    "antenna_label",
    "physical_port",
    "usage_antenna_number",
    "inventory_count",
    "read_count",
    "skip_count",
]


def _select_sequential_8ch_inventory_targets(connected_targets):
    """接続OKアンテナから、順次Inventory対象を選択します。"""
    available_targets = build_8ch_inventory_targets(connected_targets)
    if not available_targets:
        print("8CH Inventoryに使用できる接続OKアンテナがありません。")
        return []

    print("")
    print("=== 8CH複数アンテナ順次Inventory対象選択 ===")
    print("接続OKアンテナだけを候補として表示します。")
    for target in available_targets:
        print(format_8ch_inventory_candidate(target))
    print("選択例: 1 / 1,3 / all / q")
    print("複数選択時は、入力順にアンテナを切り替えてInventoryします。")

    while True:
        value = input("8CH Inventoryに使用するANT番号を入力してください（終了は'q'）: ").strip()
        try:
            selected_targets = parse_8ch_inventory_selection_input(available_targets, value)
        except ValueError as exc:
            print(f"入力エラー: {exc}")
            continue

        if selected_targets is None:
            print("8CH順次Inventory対象選択を中止しました。")
            return []

        selected_text = " -> ".join(target.label for target in selected_targets)
        print(f"選択順: {selected_text}")
        return selected_targets


def _parse_restore_usage_antenna_target_input(available_targets, value):
    """終了前に戻すANTを1つだけ選択します。"""
    normalized = value.strip().lower()
    if normalized in {"q", "quit", "cancel"}:
        return None
    if normalized == "":
        raise ValueError("空入力です。例: 1")
    if normalized == "all":
        raise ValueError("戻し先は1つだけ入力してください。all は使用できません。")
    if "," in normalized:
        raise ValueError("戻し先は1つだけ入力してください。複数指定は使用できません。")

    try:
        selected_port = int(normalized)
    except ValueError as exc:
        raise ValueError("戻し先ANT番号は数値で入力してください。") from exc

    target_by_port = {target.physical_port: target for target in available_targets}
    if selected_port not in target_by_port:
        raise ValueError("候補に表示されているANT番号を入力してください。")
    return target_by_port[selected_port]


def _build_8ch_sequential_inventory_summary(
    selected_targets,
    total_inventory_attempts: int,
    total_read_time: float,
    total_read_count: int,
    ant_read_counts: dict[str, int],
    ant_inventory_counts: dict[str, int],
    ant_skip_counts: dict[str, int],
    last_used_antenna_label: str | None,
    restore_result: dict[str, Any],
    saved_at: str | None = None,
) -> dict[str, Any]:
    """8CH順次InventoryのANT別サマリを保存しやすい形に整えます。

    PC+UIIは保存しません。公開ログやGitHubへ貼り付ける前提でも扱いやすいよう、
    ANT別の集計値だけを保存します。
    """
    selected_order = [target.label for target in selected_targets]
    ant_results = []
    for target in selected_targets:
        label = target.label
        ant_results.append(
            {
                "antenna_label": label,
                "physical_port": target.physical_port,
                "usage_antenna_number": target.usage_antenna_number_hex,
                "inventory_count": ant_inventory_counts.get(label, 0),
                "read_count": ant_read_counts.get(label, 0),
                "skip_count": ant_skip_counts.get(label, 0),
            }
        )

    return {
        "saved_at": saved_at or datetime.now().isoformat(timespec="seconds"),
        "target_model": SUMMARY_TARGET_MODEL,
        "selected_order": selected_order,
        "total_inventory_attempts": total_inventory_attempts,
        "total_read_time_seconds": round(total_read_time, 3),
        "total_read_count": total_read_count,
        "last_used_antenna_label": last_used_antenna_label,
        "restore": restore_result,
        "ant_results": ant_results,
        "privacy_note": "PC+UII values are not stored in this 8CH summary.",
    }


def _summary_to_csv_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """8CHサマリをANT別CSV行へ変換します。"""
    restore = summary.get("restore", {})
    base = {
        "saved_at": summary["saved_at"],
        "target_model": summary["target_model"],
        "selected_order": " -> ".join(summary.get("selected_order", [])),
        "total_inventory_attempts": summary["total_inventory_attempts"],
        "total_read_time_seconds": summary["total_read_time_seconds"],
        "total_read_count": summary["total_read_count"],
        "last_used_antenna_label": summary.get("last_used_antenna_label") or "",
        "restore_requested": restore.get("requested", False),
        "restore_target_label": restore.get("target_label") or "",
        "restore_success": "" if restore.get("success") is None else restore["success"],
        "restore_message": restore.get("message") or "",
    }

    rows = []
    for item in summary.get("ant_results", []):
        rows.append(
            {
                **base,
                "antenna_label": item["antenna_label"],
                "physical_port": item["physical_port"],
                "usage_antenna_number": item["usage_antenna_number"],
                "inventory_count": item["inventory_count"],
                "read_count": item["read_count"],
                "skip_count": item["skip_count"],
            }
        )
    return rows


def _append_8ch_summary_to_csv(filename: str, summary: dict[str, Any]) -> None:
    """8CH ANT別サマリをUTF-8 BOM付きCSVへ追記します。"""
    path = Path(filename)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(_summary_to_csv_rows(summary))


def _append_8ch_summary_to_json(filename: str, summary: dict[str, Any]) -> None:
    """8CHサマリをJSON履歴へ追記します。"""
    path = Path(filename)
    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8") as file:
            history = json.load(file)
        if not isinstance(history, list):
            raise ValueError("8CH summary JSON file must contain a list")
    else:
        history = []

    history.append(summary)
    with path.open("w", encoding="utf-8") as file:
        # Windows PowerShell の type/Get-Content で文字化けしにくいよう、JSONはASCIIエスケープで保存します。
        json.dump(history, file, ensure_ascii=True, indent=2)
        file.write("\n")


def _save_8ch_sequential_summary_files(
    summary: dict[str, Any],
    csv_filename: str = SUMMARY_CSV_FILENAME,
    json_filename: str = SUMMARY_JSON_FILENAME,
) -> None:
    """8CH順次InventoryサマリをCSV/JSONへ保存します。"""
    _append_8ch_summary_to_csv(csv_filename, summary)
    _append_8ch_summary_to_json(json_filename, summary)
    print(f"8CH順次InventoryサマリCSVを保存しました: {csv_filename}")
    print(f"8CH順次InventoryサマリJSONを保存しました: {json_filename}")


def _build_and_confirm_usage_antenna_dry_runs(selected_targets):
    """選択ANTの使用アンテナ番号設定フレームをまとめて表示し、1回だけ確認します。"""
    dry_runs = [build_sun02_8ch_usage_antenna_command_dry_run(target) for target in selected_targets]

    print("")
    print("=== 8CH使用アンテナ番号設定 dry-run 一覧 ===")
    for index, dry_run in enumerate(dry_runs, start=1):
        print("")
        print(f"[{index}/{len(dry_runs)}]")
        for line in format_8ch_usage_antenna_command_dry_run(dry_run):
            print(line)

    print("")
    print("上記の使用アンテナ番号設定を、Inventory前に選択順で送信します。")
    print("ここで送信するのはコマンドモード用パラメータです。FLASHは変更しません。")
    print("送信出力、周波数、UHF_SET_INVENTORY_PARAMは変更しません。")
    if not ask_yes_no("この内容で順次Inventoryを開始しますか？ [y/N]: ", default=False):
        print("使用アンテナ番号設定は送信しません。Inventoryも実行しません。")
        return []

    return dry_runs


def _send_usage_antenna_setting(ser: serial.Serial, dry_run) -> bool:
    """1つのANTについて使用アンテナ番号設定を送信します。"""
    target = dry_run.target

    print("")
    print(f"--- 使用アンテナ番号設定: {target.label} ---")
    print(f"送信フレーム: {dry_run.frame_hex}")
    response = communicate(ser, dry_run.frame)

    if _is_ack(response):
        print("使用アンテナ番号設定コマンド: ACK")
        print(f"設定対象: {target.label} / 使用アンテナ番号 {target.usage_antenna_number_hex}")
        return True

    if _is_nack(response):
        print("使用アンテナ番号設定コマンド: NACK")
        print_nack_message(response)
        print(f"{target.label} はスキップします。")
        return False

    print("使用アンテナ番号設定コマンド: ACK/NACKなし")
    print(f"Raw: {response.hex().upper()}")
    print(f"{target.label} はスキップします。")
    return False


def _run_sequential_inventory_loop(ser: serial.Serial, dry_runs) -> tuple[int, float, int, dict[str, int], dict[str, int], dict[str, int], str | None]:
    """選択ANTを順番に切り替えながらInventoryを実行します。"""
    total_inventory_attempts = 0
    total_read_time = 0.0
    total_read_count = 0
    ant_read_counts = {dry_run.target.label: 0 for dry_run in dry_runs}
    ant_inventory_counts = {dry_run.target.label: 0 for dry_run in dry_runs}
    ant_skip_counts = {dry_run.target.label: 0 for dry_run in dry_runs}
    last_used_antenna_label = None

    buzzer_enabled = ask_yes_no("読み取り結果をブザーで通知しますか？ [y/N]: ", default=False)
    mask_pc_uii_display = ask_yes_no("PC+UIIを画面表示でマスクしますか？ [y/N]: ", default=False)
    if mask_pc_uii_display:
        print("PC+UIIは画面表示で省略します。")

    print("")
    print("=== 8CH複数アンテナ順次Inventory ===")
    print("選択順: " + " -> ".join(dry_run.target.label for dry_run in dry_runs))

    while True:
        repeat_count_str = input("選択ANT一巡を繰り返す回数を入力してください（1〜100、終了は'q'）: ").strip()
        if repeat_count_str.lower() == "q":
            break
        try:
            repeat_count = int(repeat_count_str)
            if not (1 <= repeat_count <= 100):
                raise ValueError("1から100の範囲で入力してください")
        except ValueError as exc:
            print(f"入力エラー: {exc}。再度入力してください。")
            continue

        start_time = time.time()
        stop_current_request = False

        for cycle_index in range(repeat_count):
            print("")
            print(f"=== ANT順次Inventory {cycle_index + 1}/{repeat_count} ===")

            for dry_run in dry_runs:
                target = dry_run.target
                label = target.label

                if not _send_usage_antenna_setting(ser, dry_run):
                    ant_skip_counts[label] += 1
                    continue
                last_used_antenna_label = label

                print("")
                print(f"--- {label} Inventory ---")
                result = communicate(ser, COMMANDS["UHF_INVENTORY"])
                total_inventory_attempts += 1
                ant_inventory_counts[label] += 1

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
                print(f"確認対象アンテナ: {label} / 使用アンテナ番号 {target.usage_antenna_number_hex}")

                for pc_uii, rssi_value in zip(pc_uii_list, rssi_list):
                    pc_uii_hex = pc_uii.hex().upper()
                    print(f"PC+UII: {format_pc_uii_for_display(pc_uii_hex, mask=mask_pc_uii_display)}")
                    print(f"RSSI: {rssi_value:.1f} dBm")

                read_count = len(pc_uii_list)
                ant_read_counts[label] += read_count
                total_read_count += read_count

                if buzzer_enabled:
                    play_buzzer_for_inventory_result(
                        ser,
                        has_tag=read_count > 0,
                        has_nack=has_nack,
                    )
                if should_stop_inventory_repeat(has_nack):
                    print("NACK応答を受信したため、指定回数の残り読み取りを中断します。")
                    stop_current_request = True
                    break

            if stop_current_request:
                break

        total_read_time += time.time() - start_time
        print(f"現在の合計読み取り時間: {total_read_time:.2f} 秒")
        print(f"現在の合計読み取り枚数: {total_read_count} 枚")
        print("ANT別読み取り枚数:")
        for dry_run in dry_runs:
            label = dry_run.target.label
            print(
                f"  {label}: {ant_read_counts[label]} 枚 "
                f"/ Inventory実行 {ant_inventory_counts[label]} 回 "
                f"/ スキップ {ant_skip_counts[label]} 回"
            )

    return (
        total_inventory_attempts,
        total_read_time,
        total_read_count,
        ant_read_counts,
        ant_inventory_counts,
        ant_skip_counts,
        last_used_antenna_label,
    )


def _restore_usage_antenna_before_exit(ser: serial.Serial, selected_targets, last_used_antenna_label: str | None) -> dict[str, Any]:
    """終了前に使用アンテナ番号を選択ANTのいずれかへ戻します。"""
    last_used_text = last_used_antenna_label if last_used_antenna_label is not None else "なし"
    print("")
    print(f"最後に使用したANT: {last_used_text}")
    if not ask_yes_no("終了前に使用アンテナ番号を戻しますか？ [y/N]: ", default=False):
        print("終了前の使用アンテナ番号戻しは行いません。")
        return {
            "requested": False,
            "target_label": None,
            "success": None,
            "message": "not_requested",
        }

    print("")
    print("=== 終了前に戻す使用アンテナ番号の選択 ===")
    print("今回選択した接続OKアンテナだけを候補として表示します。")
    for target in selected_targets:
        print(format_8ch_inventory_candidate(target))
    print("選択例: 1 / 3 / q")
    print("戻し先は1つだけ入力してください。all と複数指定は使用できません。")

    while True:
        value = input("終了前に戻すANT番号を入力してください（中止は'q'）: ").strip()
        try:
            restore_target = _parse_restore_usage_antenna_target_input(selected_targets, value)
        except ValueError as exc:
            print(f"入力エラー: {exc}")
            continue

        if restore_target is None:
            print("終了前の使用アンテナ番号戻しを中止しました。")
            return {
                "requested": True,
                "target_label": None,
                "success": None,
                "message": "canceled",
            }
        break

    dry_run = build_sun02_8ch_usage_antenna_command_dry_run(restore_target)
    print("")
    print("=== 終了前 使用アンテナ番号戻し dry-run ===")
    for line in format_8ch_usage_antenna_command_dry_run(dry_run):
        print(line)
    print("ここで送信するのはコマンドモード用パラメータです。FLASHは変更しません。")
    print("送信出力、周波数、UHF_SET_INVENTORY_PARAMは変更しません。")
    if not ask_yes_no("この内容で使用アンテナ番号を戻しますか？ [y/N]: ", default=False):
        print("終了前の使用アンテナ番号戻しを中止しました。")
        return {
            "requested": True,
            "target_label": restore_target.label,
            "success": None,
            "message": "canceled_before_send",
        }

    print("")
    print(f"--- 終了前 使用アンテナ番号戻し: {restore_target.label} ---")
    print(f"送信フレーム: {dry_run.frame_hex}")
    response = communicate(ser, dry_run.frame)
    if _is_ack(response):
        display_message = f"戻し完了: {restore_target.label} / 使用アンテナ番号 {restore_target.usage_antenna_number_hex}"
        print(display_message)
        return {
            "requested": True,
            "target_label": restore_target.label,
            "success": True,
            "message": "completed",
        }

    if _is_nack(response):
        print("戻し失敗: NACK")
        print_nack_message(response)
        return {
            "requested": True,
            "target_label": restore_target.label,
            "success": False,
            "message": "nack",
        }

    print("戻し失敗: ACK/NACKなし")
    print(f"Raw: {response.hex().upper()}")
    return {
        "requested": True,
        "target_label": restore_target.label,
        "success": False,
        "message": "no_ack_or_nack",
    }


def _ask_and_save_8ch_sequential_summary(
    selected_targets,
    total_inventory_attempts: int,
    total_read_time: float,
    total_read_count: int,
    ant_read_counts: dict[str, int],
    ant_inventory_counts: dict[str, int],
    ant_skip_counts: dict[str, int],
    last_used_antenna_label: str | None,
    restore_result: dict[str, Any],
) -> None:
    """8CH順次InventoryのANT別サマリ保存を確認して実行します。"""
    if total_inventory_attempts <= 0:
        print("Inventory未実行のため、8CH順次Inventoryサマリは保存しません。")
        return

    print("")
    print("8CH順次InventoryのANT別サマリをCSV/JSONへ保存できます。")
    print("このサマリにはPC+UIIを保存しません。ANT別の集計値だけを保存します。")
    if not ask_yes_no("8CH順次InventoryのANT別サマリを保存しますか？ [y/N]: ", default=False):
        print("8CH順次Inventoryサマリは保存しません。")
        return

    summary = _build_8ch_sequential_inventory_summary(
        selected_targets=selected_targets,
        total_inventory_attempts=total_inventory_attempts,
        total_read_time=total_read_time,
        total_read_count=total_read_count,
        ant_read_counts=ant_read_counts,
        ant_inventory_counts=ant_inventory_counts,
        ant_skip_counts=ant_skip_counts,
        last_used_antenna_label=last_used_antenna_label,
        restore_result=restore_result,
    )
    _save_8ch_sequential_summary_files(summary)


def main() -> None:
    """UTR-SUN02-8CHの複数アンテナ順次Inventory確認を行います。"""
    print("UTR-SUN02-8CH 複数アンテナ順次Inventory確認を開始します。")
    print("FLASH、送信出力、周波数、Inventoryパラメータは変更しません。")
    print("使用アンテナ番号は、確認後にコマンドモード用パラメータへ順番に送信します。")

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
        if identified_model_key != "UTR-SUN02-8CH":
            print("このCLIの実送信対象は UTR-SUN02-8CH / USM08 のみです。")
            return

        _set_command_mode(ser)
        read_and_print_pre_inventory_reader_settings(ser)
        _read_inventory_parameters(ser)

        profile = get_model_profile(identified_model_key)
        connected_targets = check_and_print_antennas(ser, profile)
        selected_targets = _select_sequential_8ch_inventory_targets(connected_targets)
        if not selected_targets:
            return

        dry_runs = _build_and_confirm_usage_antenna_dry_runs(selected_targets)
        if not dry_runs:
            return

        (
            total_inventory_attempts,
            total_read_time,
            total_read_count,
            ant_read_counts,
            ant_inventory_counts,
            ant_skip_counts,
            last_used_antenna_label,
        ) = _run_sequential_inventory_loop(ser, dry_runs)

        print("")
        print("=== 8CH複数アンテナ順次Inventory結果まとめ ===")
        print("選択順: " + " -> ".join(dry_run.target.label for dry_run in dry_runs))
        print(f"Inventory実行回数: {total_inventory_attempts}")
        print(f"合計読み取り時間: {total_read_time:.2f} 秒")
        print(f"合計読み取り枚数: {total_read_count} 枚")
        print("ANT別結果:")
        for dry_run in dry_runs:
            label = dry_run.target.label
            print(
                f"  {label}: 読み取り {ant_read_counts[label]} 枚 "
                f"/ Inventory実行 {ant_inventory_counts[label]} 回 "
                f"/ スキップ {ant_skip_counts[label]} 回"
            )
        restore_result = _restore_usage_antenna_before_exit(ser, selected_targets, last_used_antenna_label)
        _ask_and_save_8ch_sequential_summary(
            selected_targets=selected_targets,
            total_inventory_attempts=total_inventory_attempts,
            total_read_time=total_read_time,
            total_read_count=total_read_count,
            ant_read_counts=ant_read_counts,
            ant_inventory_counts=ant_inventory_counts,
            ant_skip_counts=ant_skip_counts,
            last_used_antenna_label=last_used_antenna_label,
            restore_result=restore_result,
        )
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了します。")
    except Exception as exc:
        print("")
        print("8CH複数アンテナ順次Inventory確認中にエラーが発生しました。")
        print(f"エラー内容: {exc}")
    finally:
        if ser is not None:
            close_serial_safely(ser)


if __name__ == "__main__":
    main()
