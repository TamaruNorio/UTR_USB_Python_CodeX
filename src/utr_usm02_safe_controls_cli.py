#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02のブザー・ANT・開始CHを一時変更して復元するPhase 2 CLI。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.utr_usm02_safe_controls import execute_safe_controls
from src.utr_usm02_v117_validation_cli import collect_bootstrap_profile


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="USM02 Phase 2安全制御確認")
    parser.add_argument("--execute", action="store_true", help="実機送信を明示的に許可")
    parser.add_argument("--port", default="COM6")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--target-antenna", type=int, default=1)
    parser.add_argument("--test-channel", type=int, help="省略時は許可済み26〜32chから自動選択")
    parser.add_argument(
        "--verify-rf-channel",
        action="store_true",
        help="一時変更後にInventoryを1回実行し、実使用ANT/CHを確認",
    )
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    print("=== USM02 Phase 2 ===")
    print("1. ブザー（応答要求あり）")
    print(f"2. コマンドモードRAMのANT{args.target_antenna}一時切替・読戻し・復元")
    print("3. コマンドモードRAMの開始CH一時変更・読戻し・復元")
    if args.verify_rf_channel:
        print("4. Inventoryを1回実行し、タグ固有値を保存せず実使用ANT/CHを確認")
    print(
        "FLASH変更なし / タグ書込なし / "
        f"RF送信={'Inventory 1回のみ' if args.verify_rf_channel else 'なし'}"
    )

    if not args.execute:
        print("dry-run完了。実機送信には --execute が必要です。")
        return 0

    import serial

    from src.utr_usb_sample_legacy import communicate

    with serial.Serial(port=args.port, baudrate=args.baudrate, timeout=0.05) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        profile = collect_bootstrap_profile(ser, communicate)
        result = execute_safe_controls(
            ser,
            profile,
            communicate,
            target_antenna=args.target_antenna,
            requested_channel=args.test_channel,
            verify_rf_channel=args.verify_rf_channel,
        )

    print("ブザーACK:", "OK" if result.buzzer_ack_verified else "NG")
    print("アンテナ:", list(result.original_antenna), "->", result.temporary_antenna, "-> 復元")
    print("アンテナ復元:", "OK" if result.antenna_restored else "NG")
    print("開始CH:", result.original_starting_channel, "->", result.temporary_starting_channel, "-> 復元")
    print("周波数復元:", "OK" if result.frequency_restored else "NG")
    print("使用許可CH:", "変更なし" if result.enabled_channels_unchanged else "要確認")
    if result.rf_transmission_executed:
        print("RF送信: Inventory 1回")
        print("タグ応答数:", result.inventory_tag_response_count)
        print("タグ応答ANT:", list(result.observed_tag_antennas))
        print("完了ACK実使用CH:", result.observed_rf_channel)
    else:
        print("RF送信: なし")

    if args.json_out:
        payload = {
            "target": "UTR-SUN02-4CH / USM02",
            "rom": profile.rom.firmware_version,
            "port": args.port,
            "baudrate": args.baudrate,
            "result": result.to_dict(),
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("JSON出力:", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
