#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USB通信フレームの純粋な解析ヘルパー。

このモジュールは、STX/ETX/SUM/CR などのプロトコル上の
フレーム処理だけを扱います。

重要:
- USB実機通信は行いません。
- pyserial は import しません。
- COMポート選択、ユーザー入力、画面表示は行いません。
- 関数は引数を受け取り、戻り値で結果を返します。
"""

from typing import Optional, Tuple


# フレームの基本構造:
# STX, アドレス, コマンド, データ長, データ部..., ETX, SUM, CR
HEADER_LENGTH: int = 4
FOOTER_LENGTH: int = 3

# フレーム制御用の固定バイトです。
STX: bytes = b"\x02"
ETX: bytes = b"\x03"
CR: bytes = b"\x0D"

# 応答種別を表すコマンドバイトです。
ACK: bytes = b"\x30"
NACK: bytes = b"\x31"

# フレーム内の参照位置です。
CMD_LOCATION: int = 2
DETAIL_LOCATION: int = 4


def parse_little_endian_u16(data: bytes) -> int:
    """2バイトの little-endian 値を符号なし 16bit 整数として読み取ります。

    Args:
        data: 下位バイト、上位バイトの順で並んだ 2 バイト列。

    Returns:
        0 から 65535 の整数値。

    Raises:
        ValueError: 2 バイト以外が渡された場合。
    """
    if len(data) != 2:
        raise ValueError("little-endian 16bit value must be exactly 2 bytes")

    return int.from_bytes(data, byteorder="little", signed=False)


def calculate_sum_value(data: bytes) -> int:
    """SUM値を計算します。

    UTRの通信フレームでは、STXからETXまでの各バイトを合計し、
    下位1バイトをSUMとして扱います。

    Args:
        data: SUM計算対象のバイト列。通常はSTXからETXまでです。

    Returns:
        合計値の下位1バイト。
    """
    sum_value = 0
    for byte in data:
        sum_value += byte
    return sum_value & 0xFF


def verify_sum_value(data_frame: bytes) -> bool:
    """フレーム内のSUM値が正しいか検証します。

    `data_frame` は STX から CR までを含む完全なフレームを想定します。
    最後から2バイト目を期待SUM値とし、STXからETXまでを再計算して
    一致するかを確認します。

    Args:
        data_frame: STXからCRまでの1フレーム。

    Returns:
        SUMが一致すればTrue、一致しなければFalse。
    """
    if len(data_frame) < (HEADER_LENGTH + FOOTER_LENGTH):
        return False

    expected_sum_value = data_frame[-2]
    calculated_sum_value = calculate_sum_value(data_frame[:-2])
    return expected_sum_value == calculated_sum_value


def parse_nack_response(nack_response: bytes) -> str:
    """NACK応答のエラーコードを説明文に変換します。

    現行サンプルと同じく、エラーコードは index 5 にある前提です。
    コード表の完全性は要プロトコル仕様書確認です。

    Args:
        nack_response: NACK応答フレーム。

    Returns:
        エラー説明文。未知のコードは `Unknown NACK error` として返します。
    """
    if len(nack_response) < (HEADER_LENGTH + FOOTER_LENGTH):
        return "Invalid NACK response"

    error_code = nack_response[5]

    error_messages = {
        0x01: "CMD_CRC_ERROR: データのCRCが一致しない",
        0x02: "CMD_TIME_OVER: データが途中で途切れた",
        0x03: "CMD_RX_ERROR: アンチコリジョン処理中にエラー",
        0x04: "CMD_RXBUSY_ERROR: RFタグからの応答がない",
        0x07: "CMD_ERROR: コマンド実行中にリーダライタ内部でエラー",
        0x0A: "CMD_UHF_IC_ERROR: RFタグアクセス時の内部チップエラー",
        0x60: "CMD_LBT_ERROR: キャリアセンス時のタイムアウトエラー",
        0x64: "HARDWARE_ERROR: ハードウェア内部で異常が発生",
        0x68: "CMD_ANT_ERROR: アンテナ断線検知エラー",
        0x42: "SUM_ERROR: 上位機器から送信されたコマンドのSUM値が正しくない",
        0x44: "FORMAT_ERROR: 上位機器から送信されたコマンドのフォーマットまたはパラメータが正しくない",
    }

    return error_messages.get(error_code, f"Unknown NACK error (0x{error_code:02X})")


def parse_data_frame(data: bytes, index: int) -> Tuple[Optional[bytes], int]:
    """受信バイト列から1フレームを切り出します。

    指定された `index` から始まるデータについて、ヘッダのデータ長を見て、
    STXからCRまでの完全なフレームが存在するかを確認します。

    Args:
        data: 受信済みのバイト列。
        index: フレーム解析を開始する位置。

    Returns:
        `(frame, next_index)` のタプルです。
        完全なフレームがあれば `frame` に bytes を返し、`next_index` は
        次の解析開始位置になります。見つからなければ `frame` は None、
        `next_index` は元の index のままです。
    """
    minimum_length = index + HEADER_LENGTH + FOOTER_LENGTH
    if len(data) < minimum_length:
        return None, index

    data_length_in_frame = data[index + 3]
    total_frame_length = data_length_in_frame + HEADER_LENGTH + FOOTER_LENGTH

    if len(data) < (index + total_frame_length):
        return None, index

    frame_end = index + total_frame_length
    if data[frame_end - 1] != CR[0]:
        return None, index

    return data[index:frame_end], frame_end
