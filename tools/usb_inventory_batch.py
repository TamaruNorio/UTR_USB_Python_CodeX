#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USB接続版 UTR Inventory batch CSV runner.

安全方針:
- UHF_INVENTORY の連続実行とCSV保存だけを行います。
- UHF_SET_INVENTORY_PARAM は送信しません。
- FLASH、送信出力、周波数、8CHアンテナ切替は変更しません。
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

import serial

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utr_usb_inventory_with_output_power import (  # noqa: E402
    _is_nack,
    _read_inventory_parameters,
    _set_command_mode,
    _verify_usb_and_read_model_key,
)
from src.utr_usb_sample import (  # noqa: E402
    COMMANDS,
    close_serial_safely,
    communicate,
    play_buzzer_for_inventory_result,
    print_nack_message,
    read_and_print_pre_inventory_reader_settings,
    received_data_contains_nack,
    received_data_parse,
)


CSV_COLUMNS = [
    "timestamp",
    "iteration",
    "read_time_sec",
    "expected_read_count",
    "actual_tag_count",
    "rssi",
    "pc_uii",
    "output_power_dbm",
    "channel",
    "frequency_mhz",
    "note",
]


@dataclass(frozen=True)
class InventoryBatchResult:
    total_iterations: int
    total_read_time_sec: float
    total_tag_responses: int
    tag_counts: Counter[str]
    rssi_values: list[float]
    csv_path: Path

    @property
    def unique_tags(self) -> int:
        return len(self.tag_counts)

    @property
    def average_tag_count(self) -> float:
        if self.total_iterations == 0:
            return 0.0
        return self.total_tag_responses / self.total_iterations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="USB接続で UHF_INVENTORY を連続実行し、結果をCSV保存します。",
    )
    parser.add_argument("--port", help="COMポート名。例: COM6")
    parser.add_argument("--baudrate", type=int, default=115200, help="ボーレート。既定値: 115200")
    parser.add_argument("--repeat", type=int, default=10, help="Inventory実行回数。既定値: 10")
    parser.add_argument("--interval", type=float, default=0.1, help="各Inventory後の待ち時間秒。既定値: 0.1")
    parser.add_argument("--no-buzzer", action="store_true", help="読み取り結果ブザーを送信しません。")
    parser.add_argument("--csv", dest="csv_path", help="CSV保存先。未指定時は logs/usb_sample に自動作成します。")
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("--repeat は 1 以上を指定してください。")
    if args.interval < 0:
        parser.error("--interval は 0 以上を指定してください。")
    if args.baudrate < 1:
        parser.error("--baudrate は 1 以上を指定してください。")
    if not args.port:
        parser.error("--port を指定してください。例: --port COM6")
    return args


def _default_csv_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "logs" / "usb_sample" / f"inventory_batch_{timestamp}.csv"


def _resolve_csv_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    return _default_csv_path()


def _format_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


def _write_summary_rows(writer: csv.writer, result: InventoryBatchResult) -> None:
    writer.writerow(["SUMMARY", "total_iterations", str(result.total_iterations)])
    writer.writerow(["SUMMARY", "total_read_time_sec", f"{result.total_read_time_sec:.3f}"])
    writer.writerow(["SUMMARY", "total_tag_responses", str(result.total_tag_responses)])
    writer.writerow(["SUMMARY", "unique_tags", str(result.unique_tags)])
    writer.writerow(["SUMMARY", "average_tag_count", f"{result.average_tag_count:.3f}"])
    if result.rssi_values:
        writer.writerow(["SUMMARY", "min_rssi", f"{min(result.rssi_values):.3f}"])
        writer.writerow(["SUMMARY", "max_rssi", f"{max(result.rssi_values):.3f}"])
        writer.writerow(["SUMMARY", "average_rssi", f"{sum(result.rssi_values) / len(result.rssi_values):.3f}"])
    else:
        writer.writerow(["SUMMARY", "min_rssi", ""])
        writer.writerow(["SUMMARY", "max_rssi", ""])
        writer.writerow(["SUMMARY", "average_rssi", ""])


def _print_summary(result: InventoryBatchResult) -> None:
    print("")
    print("=== 集計結果 ===")
    print(f"Inventory回数: {result.total_iterations}")
    print(f"総読み取り時間: {result.total_read_time_sec:.3f} 秒")
    print(f"総タグ応答数: {result.total_tag_responses}")
    print(f"ユニークタグ数: {result.unique_tags}")
    print(f"平均タグ応答数: {result.average_tag_count:.3f}")
    if result.rssi_values:
        print(f"RSSI最小値: {min(result.rssi_values):.3f}")
        print(f"RSSI最大値: {max(result.rssi_values):.3f}")
        print(f"RSSI平均値: {sum(result.rssi_values) / len(result.rssi_values):.3f}")
    else:
        print("RSSI集計: 読み取りなし")
    print("タグ別読み取り回数:")
    if result.tag_counts:
        for pc_uii, count in result.tag_counts.most_common():
            print(f"  {pc_uii}: {count} 回")
    else:
        print("  なし")
    print(f"CSV保存先: {result.csv_path}")


def _run_inventory_batch(
    ser: serial.Serial,
    *,
    repeat: int,
    interval: float,
    buzzer_enabled: bool,
    csv_path: Path,
) -> InventoryBatchResult:
    total_read_time_sec = 0.0
    total_tag_responses = 0
    tag_counts: Counter[str] = Counter()
    rssi_values: list[float] = []

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_COLUMNS)

        for iteration in range(1, repeat + 1):
            iteration_timestamp = datetime.now().isoformat(timespec="milliseconds")
            start_time = time.perf_counter()
            response = communicate(ser, COMMANDS["UHF_INVENTORY"])
            read_time_sec = time.perf_counter() - start_time
            total_read_time_sec += read_time_sec

            expected_count = None
            read_channel = None
            actual_tag_count = 0
            note = "NO_RESPONSE"
            pc_uii_list: list[bytes] = []
            rssi_list: list[float] = []

            if response:
                has_nack = received_data_contains_nack(response)
                if _is_nack(response):
                    note = "NACK"
                    print_nack_message(response)
                else:
                    pc_uii_list, rssi_list, expected_count, read_channel = received_data_parse(response)
                    actual_tag_count = len(pc_uii_list)
                    note = "OK" if actual_tag_count else "NO_TAG"
                    if expected_count is not None:
                        print(f"[{iteration}/{repeat}] 読み取り完了レスポンス枚数: {expected_count} 枚")
                    if read_channel is not None:
                        print(f"[{iteration}/{repeat}] 読み取りチャンネル: {read_channel} ch")
                    print(f"[{iteration}/{repeat}] タグ応答数: {actual_tag_count}")

                if buzzer_enabled:
                    play_buzzer_for_inventory_result(
                        ser,
                        has_tag=actual_tag_count > 0,
                        has_nack=has_nack,
                    )
            else:
                print(f"[{iteration}/{repeat}] インベントリ応答がありませんでした。")
                if buzzer_enabled:
                    play_buzzer_for_inventory_result(ser, has_tag=False, has_nack=False)

            if pc_uii_list:
                for pc_uii, rssi in zip(pc_uii_list, rssi_list):
                    pc_uii_hex = pc_uii.hex().lower()
                    tag_counts[pc_uii_hex] += 1
                    rssi_values.append(rssi)
                    total_tag_responses += 1
                    writer.writerow([
                        iteration_timestamp,
                        iteration,
                        f"{read_time_sec:.3f}",
                        _format_optional_int(expected_count),
                        actual_tag_count,
                        f"{rssi:.3f}",
                        pc_uii_hex,
                        "",
                        _format_optional_int(read_channel),
                        "",
                        note,
                    ])
            else:
                writer.writerow([
                    iteration_timestamp,
                    iteration,
                    f"{read_time_sec:.3f}",
                    _format_optional_int(expected_count),
                    actual_tag_count,
                    "",
                    "",
                    "",
                    _format_optional_int(read_channel),
                    "",
                    note,
                ])

            if iteration < repeat and interval > 0:
                time.sleep(interval)

        result = InventoryBatchResult(
            total_iterations=repeat,
            total_read_time_sec=total_read_time_sec,
            total_tag_responses=total_tag_responses,
            tag_counts=tag_counts,
            rssi_values=rssi_values,
            csv_path=csv_path,
        )
        _write_summary_rows(writer, result)

    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    csv_path = _resolve_csv_path(args.csv_path)

    print("USB Inventory batch CSV runner を開始します。")
    print("FLASH、送信出力、周波数、Inventoryパラメータ、8CHアンテナ切替は変更しません。")
    print(f"CSV保存先: {csv_path}")

    ser: serial.Serial | None = None
    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            timeout=0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"接続成功: {args.port} @ {args.baudrate}bps")

        _verify_usb_and_read_model_key(ser)
        _set_command_mode(ser)
        read_and_print_pre_inventory_reader_settings(ser)
        _read_inventory_parameters(ser)

        result = _run_inventory_batch(
            ser,
            repeat=args.repeat,
            interval=args.interval,
            buzzer_enabled=not args.no_buzzer,
            csv_path=csv_path,
        )
        _print_summary(result)
        return 0
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了します。")
        return 130
    except Exception as exc:
        print("")
        print("USB Inventory batch CSV runner でエラーが発生しました。")
        print(f"エラー内容: {exc}")
        return 1
    finally:
        if ser is not None:
            close_serial_safely(ser)


if __name__ == "__main__":
    raise SystemExit(main())
