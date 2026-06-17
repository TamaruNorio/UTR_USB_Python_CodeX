#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USB sample default entry point.

既存の関数・定数は `utr_usb_sample_legacy.py` から再公開します。
通常実行時は、送信出力一時変更つきInventoryフローを起動します。

この構成により、既存テストや他モジュールからの import 互換性を維持しながら、
標準入口 `py ./src/utr_usb_sample.py` を新しいInventoryフローへ切り替えます。
"""

from __future__ import annotations

import json

try:
    from src.utr_usb_sample_legacy import *  # noqa: F401,F403
except ModuleNotFoundError:
    from utr_usb_sample_legacy import *  # noqa: F401,F403


def restore_antenna_setting_safely(ser, antenna_selection) -> None:
    """中断時でも可能な限りコマンドモード用アンテナ設定を復元します。"""
    if antenna_selection is None:
        return

    clear_serial_input_buffer_before_restore(ser)

    try:
        restored = restore_command_mode_antenna_setting(ser, antenna_selection.restore_setting)
    except Exception as exc:
        print("コマンドモード用アンテナ設定の復元に失敗しました。")
        print("機器側の現在設定をUTRRWManagerまたは再実行時の読み取りで確認してください。")
        print(f"復元エラー: {exc}")
        return
    if not restored:
        print("コマンドモード用アンテナ設定の復元に失敗しました。")
        print("機器側の現在設定をUTRRWManagerまたは再実行時の読み取りで確認してください。")


def save_inventory_results(
    total_iterations: int,
    total_read_time: float,
    total_read_count: int,
    pc_uii_count_dict: dict,
    inventory_result_items: list[dict],
) -> None:
    """Inventory集計結果をTXT/CSV/JSONへ保存します。"""
    if not should_save_inventory_results(total_iterations):
        print("Inventoryが実行されていないため、集計結果は保存しません。")
        return

    try:
        save_results_to_file(
            "inventory_results.txt",
            total_iterations,
            total_read_time,
            total_read_count,
            pc_uii_count_dict,
        )
        print("集計結果を inventory_results.txt に保存しました。")
    except OSError as e:
        print(f"TXT保存エラー: {e}")

    summary = build_result_summary(
        total_iterations,
        total_read_time,
        total_read_count,
        pc_uii_count_dict,
        items=inventory_result_items,
    )
    try:
        save_results_to_csv("inventory_results.csv", summary)
        print("集計結果を inventory_results.csv に保存しました。")
    except OSError as e:
        print(f"CSV保存エラー: {e}")
    try:
        save_results_to_json("inventory_results.json", summary)
        print("集計結果を inventory_results.json に保存しました。")
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"JSON保存エラー: {e}")


def finish_inventory_session(
    ser,
    antenna_selection,
    total_iterations: int,
    total_read_time: float,
    total_read_count: int,
    pc_uii_count_dict: dict,
    inventory_result_item_dict: dict,
) -> None:
    """Inventory終了時の復元、保存、切断をまとめて実行します。"""
    restore_antenna_setting_safely(ser, antenna_selection)
    save_inventory_results(
        total_iterations,
        total_read_time,
        total_read_count,
        pc_uii_count_dict,
        list(inventory_result_item_dict.values()),
    )
    close_serial_safely(ser)


def main() -> None:
    """送信出力一時変更つきInventoryフローを起動します。"""
    try:
        from src.utr_usb_inventory_with_output_power import main as integrated_main
    except ModuleNotFoundError:
        from utr_usb_inventory_with_output_power import main as integrated_main

    integrated_main()


if __name__ == "__main__":
    main()
