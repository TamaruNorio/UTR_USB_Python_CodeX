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

from typing import List


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
    return int.from_bytes(data_frame[6:8], byteorder="little")


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
