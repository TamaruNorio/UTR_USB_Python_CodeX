#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02 ANT0〜2 Inventory・タグ検出時ブザー確認CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.utr_usm02_inventory_buzzer import execute_sequential_inventory_buzzer
from src.utr_usm02_v117_validation_cli import collect_bootstrap_profile


def parse_antenna_list(value: str) -> tuple[int, ...]:
    try:
        antennas = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("アンテナは 0,1,2 の形式で指定してください") from exc
    if not antennas:
        raise argparse.ArgumentTypeError("アンテナを1件以上指定してください")
    return antennas


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="USM02 アンテナ別Inventory・条件付きブザー確認")
    parser.add_argument("--execute", action="store_true", help="実機送信を明示的に許可")
    parser.add_argument("--port", default="COM6")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--antennas", type=parse_antenna_list, default=(0, 1, 2))
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    labels = ", ".join(f"ANT{value}" for value in args.antennas)
    print("=== USM02 アンテナ別Inventory・条件付きブザー確認 ===")
    print("対象:", labels)
    print("各ANTでInventoryを1回実行し、タグ応答が1件以上ならピッピッピ音を送信します。")
    print("開始前にROM・設定・ANT0〜3の物理接続を再取得します。")
    print("FLASH変更なし / タグ書込なし / タグ固有値の表示・保存なし")

    if not args.execute:
        print("dry-run完了。実機送信には --execute が必要です。")
        return 0

    try:
        import serial

        from src.utr_usb_sample_legacy import communicate

        with serial.Serial(port=args.port, baudrate=args.baudrate, timeout=0.05) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            profile = collect_bootstrap_profile(ser, communicate)
            result = execute_sequential_inventory_buzzer(
                ser,
                profile,
                communicate,
                target_antennas=args.antennas,
            )
    except (RuntimeError, ValueError) as exc:
        print("安全停止:", exc)
        return 1

    print("接続OKアンテナ:", list(profile.connected_antennas))
    for item in result.antenna_results:
        print(
            f"ANT{item.antenna}: タグ応答={item.tag_response_count}, "
            f"ユニークタグ={item.unique_tag_count}, 完了ACK枚数={item.completion_reported_count}, "
            f"件数照合={'OK' if item.response_count_matches_completion else '差異あり'}, "
            f"CH={item.observed_channel}, ブザーACK={'OK' if item.buzzer_ack_verified else '対象外'}"
        )
    print("アンテナ復元:", "OK" if result.antenna_restored else "NG")
    print("実際に音が聞こえたかは、ANTごとにユーザー確認が必要です。")

    if args.json_out:
        payload = {
            "target": "UTR-SUN02-4CH / USM02",
            "rom": profile.rom.firmware_version,
            "port": args.port,
            "baudrate": args.baudrate,
            "audible_buzzer_confirmation": "USER_CONFIRMATION_REQUIRED",
            "result": result.to_dict(),
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("JSON出力:", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
