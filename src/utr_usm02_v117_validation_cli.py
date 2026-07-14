#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""USM02 Ver.1.17検証計画CLI。

既定はdry-runであり、COMポートを開かない。実機の事前確認だけを行う場合も
``--execute-bootstrap`` を明示する必要がある。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.utr_antenna import (
    get_model_profile,
    identify_model_key_from_rom,
    parse_antenna_switching_setting_response,
    parse_check_antenna_response,
    parse_rom_version_response,
)
from src.utr_commands import (
    COMMANDS,
    PARAMETER_KIND_COMMAND_MODE,
    build_check_antenna_command,
    build_frame,
    build_read_antenna_switching_setting_command,
)
from src.utr_device_profile import build_usm02_device_profile
from src.utr_inventory import parse_inventory_param_response
from src.utr_response_settings import parse_epc_uii_response_settings
from src.utr_response_v117 import VerificationResult, verify_command_response
from src.utr_usm02_v117_validation import HARD_SAFETY_RULES, build_validation_plan, summarize_plan
from src.utr_v117_catalog import get_command_spec


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UTR-SUN02-4CH/USM02 Ver.1.17 54コマンド検証計画")
    parser.add_argument("--port", default="COM6")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--rom-number", type=int, help="dry-run用。例: Ver.2.052は2052")
    parser.add_argument("--execute-bootstrap", action="store_true", help="ROM・設定・ANT0〜3だけを実機から読み取る")
    parser.add_argument("--json-out", type=Path, help="マスク済み計画JSONの保存先（任意）")
    return parser.parse_args()


def _print_plan(rom_number: int | None) -> tuple[dict[str, object], ...]:
    plan = build_validation_plan(rom_number)
    print("\n=== 54コマンド検証計画 ===")
    for entry in plan:
        print(f"{entry.section:6} {entry.plan_status:31} {entry.name} / 応答={entry.response_pattern} DATA長={entry.ack_data_length}")
    print("\n集計:", summarize_plan(plan))
    return tuple(entry.to_dict() for entry in plan)


def _assert_verified(section: str, response: bytes, profile, *, response_requested: bool = True) -> None:
    result = verify_command_response(
        get_command_spec(section), response, profile, response_requested=response_requested
    )
    if result.result not in {
        VerificationResult.ACK_VERIFIED,
        VerificationResult.NO_RESPONSE_VERIFIED,
        VerificationResult.CONDITIONAL_NO_RESPONSE_VERIFIED,
    }:
        raise RuntimeError(f"{section} の応答検証に失敗しました: {result.result.value}; {' / '.join(result.notes)}")


def collect_bootstrap_profile(ser, communicate):
    """接続済みserialからUSM02の応答解釈用プロファイルを収集する。"""
    rom_response = communicate(ser, COMMANDS["ROM_VERSION_CHECK"])
    rom = parse_rom_version_response(rom_response)
    model_key = identify_model_key_from_rom(rom)
    if model_key != "UTR-SUN02-4CH":
        raise RuntimeError(f"対象機種不一致のため停止します: ROM={rom.raw_text}, model={model_key}")

    # コマンドモードへ切替。FLASHは変更しない。
    mode_response = communicate(ser, COMMANDS["COMMAND_MODE_SET"])

    antenna_response = communicate(
        ser,
        build_read_antenna_switching_setting_command(PARAMETER_KIND_COMMAND_MODE),
    )
    antenna_setting = parse_antenna_switching_setting_response(antenna_response)

    model = get_model_profile(model_key)
    connected: list[int] = []
    for target in model.check_targets:
        response = communicate(ser, build_check_antenna_command(target.number))
        check = parse_check_antenna_response(response)
        if check.is_connected:
            connected.append(target.number)

    inventory_response = communicate(ser, build_frame(0x55, b"\x41\x00"))
    inventory_settings = parse_inventory_param_response(inventory_response)

    epc_command_response = communicate(ser, build_frame(0x55, b"\x43\x05\x00"))
    epc_command = parse_epc_uii_response_settings(epc_command_response)
    epc_auto_response = communicate(ser, build_frame(0x55, b"\x43\x05\x01"))
    epc_auto = parse_epc_uii_response_settings(epc_auto_response)

    profile = build_usm02_device_profile(
        rom,
        antenna_setting,
        connected,
        inventory_tid_enabled=inventory_settings["tid_enabled"],
        epc_buffering_enabled=epc_command.epc_buffering_enabled,
        read_cycle_completion_enabled=epc_auto.read_cycle_completion_enabled,
        antenna_switch_completion_enabled=epc_auto.antenna_switch_completion_enabled,
        carrier_detect_response_enabled=epc_auto.carrier_detect_response_enabled,
    )
    _assert_verified("7.4.16", mode_response, profile)
    _assert_verified("7.4.5", antenna_response, profile)
    _assert_verified("7.4.3", inventory_response, profile)
    _assert_verified("7.4.9", epc_command_response, profile)
    _assert_verified("7.4.9", epc_auto_response, profile)
    return profile


def _execute_bootstrap(port: str, baudrate: int):
    """ROM、コマンドモード設定、応答依存設定、物理ANT状態を安全に取得する。"""
    import serial

    from src.utr_usb_sample_legacy import communicate

    print(f"実機事前確認: port={port}, baudrate={baudrate}")
    with serial.Serial(port=port, baudrate=baudrate, timeout=0.05) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        profile = collect_bootstrap_profile(ser, communicate)

    print("ROM:", profile.rom.raw_text)
    print("機種:", profile.model_key)
    print("物理容量:", profile.antenna_capacity)
    print("設定アンテナ:", list(profile.configured_antennas))
    print("接続OKアンテナ:", list(profile.connected_antennas))
    print("アンテナID出力:", profile.antenna_id_output_enabled)
    print("TID付加:", profile.inventory_tid_enabled)
    print("EPCバッファリング:", profile.epc_buffering_enabled)
    print("自動読取サイクル完了応答:", profile.read_cycle_completion_enabled)
    print("自動アンテナ切替完了応答:", profile.antenna_switch_completion_enabled)
    print("キャリア検知応答:", profile.carrier_detect_response_enabled)
    return profile


def main() -> int:
    args = _parse_args()
    print("=== 強制安全ルール ===")
    for rule in HARD_SAFETY_RULES:
        print("-", rule)

    profile = None
    rom_number = args.rom_number
    if args.execute_bootstrap:
        profile = _execute_bootstrap(args.port, args.baudrate)
        rom_number = profile.rom_number

    plan = _print_plan(rom_number)
    if args.json_out:
        payload: dict[str, object] = {
            "target": "UTR-SUN02-4CH / USM02",
            "port": args.port,
            "baudrate": args.baudrate,
            "real_device_bootstrap_executed": bool(args.execute_bootstrap),
            "rom_number": rom_number,
            "profile": None if profile is None else {
                "model_key": profile.model_key,
                "rom": profile.rom.raw_text,
                "antenna_capacity": profile.antenna_capacity,
                "configured_antennas": list(profile.configured_antennas),
                "connected_antennas": list(profile.connected_antennas),
                "antenna_id_output_enabled": profile.antenna_id_output_enabled,
                "inventory_tid_enabled": profile.inventory_tid_enabled,
                "epc_buffering_enabled": profile.epc_buffering_enabled,
                "read_cycle_completion_enabled": profile.read_cycle_completion_enabled,
                "antenna_switch_completion_enabled": profile.antenna_switch_completion_enabled,
                "carrier_detect_response_enabled": profile.carrier_detect_response_enabled,
            },
            "hard_safety_rules": list(HARD_SAFETY_RULES),
            "plan": plan,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("JSON出力:", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
