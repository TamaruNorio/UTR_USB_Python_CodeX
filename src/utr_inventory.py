#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR Inventory応答を解析する純粋ヘルパー。

このモジュールは、受信済みのInventory応答フレームを解析するための
関数だけを持ちます。

重要:
- USB実機通信は行いません。
- pyserial は import しません。
- COMポート選択、ユーザー入力、画面表示は行いません。
- 関数は引数を受け取り、戻り値または引数のリスト更新で結果を返します。
"""

from typing import Any, Dict, List, Tuple

try:
    from src.utr_protocol import parse_little_endian_u16
except ModuleNotFoundError:
    # `python src/utr_usb_sample.py` のように src 配下を直接実行した場合の互換用です。
    from utr_protocol import parse_little_endian_u16


def convert_rssi(rssi_hex_value: str) -> float:
    """RSSI値をdBm相当の数値へ変換します。

    現行サンプルと同じく、RSSIを16bit符号付き整数として扱い、
    10で割った値を返します。

    注意:
        RSSIのエンディアン、符号、単位は要仕様書確認です。

    Args:
        rssi_hex_value: RSSIを表す16進文字列。例: ``"FFCE"``。

    Returns:
        変換後のRSSI値。
    """
    rssi_int = int(rssi_hex_value, 16)
    if rssi_int & 0x8000:
        rssi_int = -(0x10000 - rssi_int)
    return rssi_int / 10.0


def check_inventory_ack_response(data_frame: bytes) -> int:
    """Inventory ACKフレームから読み取り予定枚数を取得します。

    現行サンプルと同じく、index ``6:8`` の2バイトを
    little endian の整数として扱います。

    注意:
        ACKフレーム内の正確なフィールド位置は要仕様書確認です。

    Args:
        data_frame: Inventory ACKとみなすフレーム。

    Returns:
        読み取り予定枚数。
    """
    return parse_little_endian_u16(data_frame[6:8])


def parse_inventory_ack_response(data_frame: bytes) -> Tuple[int, int]:
    """Inventory ACK から読み取り枚数とチャンネル番号を返します。"""
    read_count = check_inventory_ack_response(data_frame)
    channel = data_frame[8]
    return read_count, channel


def parse_inventory_param_response(data_frame: bytes) -> Dict[str, Any]:
    """UHF_GetInventoryParam のACK応答を日本語で扱いやすい形に展開します。

    プロトコル仕様書に記載された bit 配置に従って、
    各パラメータを辞書へ分解して返します。

    Args:
        data_frame: UHF_GetInventoryParam の ACK 応答フレーム。

    Returns:
        日本語表示に使いやすい値を持つ辞書。

    Raises:
        ValueError: 応答長が不足している場合。
    """
    if len(data_frame) < 18:
        raise ValueError("inventory param response is too short")

    parameter_type = data_frame[5]
    parameter1 = data_frame[6]
    parameter2 = data_frame[7]
    parameter3 = data_frame[8]
    parameter4 = data_frame[9]
    read_start_address = int.from_bytes(data_frame[10:14], byteorder="big", signed=False)
    read_word_count = data_frame[14]

    parameter_type_map = {
        0x00: "コマンドモード用のパラメータ",
        0x01: "自動読み取りモード用パラメータ",
        0x02: "FLASHデータ",
    }
    session_map = {0: "S0", 1: "S1", 2: "S2", 3: "S3"}
    sel_map = {0: "ALL(code=0)", 1: "ALL(code=1)", 2: "^SL", 3: "SL"}
    m_map = {0: "M1", 1: "M2", 2: "M4", 3: "M8"}
    mem_bank_map = {0: "RESERVED", 1: "EPC(UII)", 2: "TID", 3: "USER"}

    return {
        "detail_command": data_frame[4],
        "parameter_type_code": parameter_type,
        "parameter_type_text": parameter_type_map.get(parameter_type, f"不明 (0x{parameter_type:02X})"),
        "select_command_enabled": bool(parameter1 & 0x01),
        "q_auto_enabled": bool(parameter1 & 0x02),
        "anti_collision_enabled": bool(parameter1 & 0x04),
        "q_start": (parameter1 >> 3) & 0x0F,
        "inventory_target": "B" if (parameter1 & 0x80) else "A",
        "session": session_map.get(parameter2 & 0x03, "要仕様書確認"),
        "sel": sel_map.get((parameter2 >> 2) & 0x03, "要仕様書確認"),
        "trext": "Use pilot tone" if (parameter2 & 0x10) else "No pilot tone",
        "m": m_map.get((parameter2 >> 5) & 0x03, "要仕様書確認"),
        "dr": "64/3" if (parameter2 & 0x80) else "8",
        "q_min": parameter3 & 0x0F,
        "q_max": (parameter3 >> 4) & 0x0F,
        "mem_bank": mem_bank_map.get(parameter4 & 0x03, "要仕様書確認"),
        "tid_enabled": bool(parameter4 & 0x04),
        "read_start_word_address": read_start_address,
        "read_start_word_address_hex": f"{read_start_address:08X}",
        "read_word_count": read_word_count,
    }


def format_inventory_param_response(parsed: Dict[str, Any]) -> List[str]:
    """解析済みインベントリパラメータを日本語表示用の行へ整形します。"""
    yes_no = lambda value: "使用する" if value else "使用しない"
    trext_text = "Use pilot tone" if parsed["trext"] == "Use pilot tone" else "No pilot tone"

    return [
        f"パラメータの種類: {parsed['parameter_type_text']}",
        f"Selectコマンド: {yes_no(parsed['select_command_enabled'])}",
        f"Q値の自動UP/DOWN機能: {yes_no(parsed['q_auto_enabled'])}",
        f"アンチコリジョン機能: {yes_no(parsed['anti_collision_enabled'])}",
        f"Q値の開始値: {parsed['q_start']}",
        f"InventoryのTarget: {parsed['inventory_target']}",
        f"Session: {parsed['session']}",
        f"Sel: {parsed['sel']}",
        f"TRext(Pilot tone): {trext_text}",
        f"M: {parsed['m']}",
        f"DR: {parsed['dr']}",
        f"Q値の最小値: {parsed['q_min']}",
        f"Q値の最大値: {parsed['q_max']}",
        f"MemBank: {parsed['mem_bank']}",
        f"TID付加: {yes_no(parsed['tid_enabled'])}",
        f"読み取り開始アドレス(Hex): {parsed['read_start_word_address_hex']}",
        f"読み取りWord数: {parsed['read_word_count']}",
    ]


def handle_inventory_response(
    data_frame: bytes,
    pc_uii_list: List[bytes],
    rssi_list: List[float],
) -> None:
    """Inventory応答フレームからPC/UIIとRSSIを取り出します。

    この関数はSUM検証を担当しません。呼び出し元が、必要に応じて
    フレーム検証済みのデータを渡す前提です。

    現行サンプルと同じく、index 8 をPC/UII長、index 9以降を
    PC/UIIデータとして扱います。RSSIは index 5:7 の2バイトを使います。

    注意:
        Inventory応答の詳細フォーマットは要仕様書確認です。

    Args:
        data_frame: Inventory応答とみなす1フレーム。
        pc_uii_list: 抽出したPC/UIIを追加するリスト。
        rssi_list: 抽出したRSSIを追加するリスト。
    """
    pc_uii_length = data_frame[8]
    pc_uii_data = data_frame[9:9 + pc_uii_length]
    pc_uii_list.append(pc_uii_data)

    rssi_value = convert_rssi(data_frame[5:7].hex())
    rssi_list.append(rssi_value)
