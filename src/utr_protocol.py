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

from typing import Any, Optional, Tuple


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


NACK_FRAME_DATA_LENGTH: int = 0x0A


NACK_ERROR_CODE_1_INFO: dict[int, dict[str, Any]] = {
    0x01: {
        "category": "RFタグ受信データ異常",
        "symbol": "CMD_CRC_ERROR",
        "technical_description": "RFタグから受信したデータのCRCが一致しません。",
        "field_message": "タグ応答が不安定、または読み取り条件が悪い可能性があります。",
        "check_points": ["タグ距離", "タグ向き", "周辺金属", "アンテナ位置", "再読み取り"],
    },
    0x02: {
        "category": "RFタグ受信タイムアウト",
        "symbol": "CMD_TIME_OVER",
        "technical_description": "RFタグからの受信データが途中で途切れました。",
        "field_message": "タグ応答が途中で途切れる条件になっている可能性があります。",
        "check_points": ["タグ距離", "タグ枚数", "電波環境", "再実行"],
    },
    0x03: {
        "category": "アンチコリジョン処理異常",
        "symbol": "CMD_RX_ERROR",
        "technical_description": "アンチコリジョン処理中にエラーが発生しました。",
        "field_message": "複数タグ読み取り条件が不安定な可能性があります。",
        "check_points": ["複数タグ有無", "タグ密集", "Q値", "再読み取り"],
    },
    0x04: {
        "category": "RFタグ応答なし",
        "symbol": "CMD_RXBUSY_ERROR",
        "technical_description": "RFタグからの応答がありません。",
        "field_message": "タグが読める位置や条件にない可能性があります。",
        "check_points": ["タグ有無", "タグ向き", "距離", "アンテナ接続", "送信出力"],
    },
    0x07: {
        "category": "リーダライタ内部処理異常",
        "symbol": "CMD_ERROR",
        "technical_description": "コマンド実行中にリーダライタ内部でエラーが発生しました。",
        "field_message": "コマンド条件または機器状態を確認してください。",
        "check_points": ["コマンド条件", "再実行", "電源再投入"],
    },
    0x0A: {
        "category": "RFタグアクセス時の内蔵チップエラー",
        "symbol": "CMD_UHF_IC_ERROR",
        "technical_description": "RFタグアクセス時、リーダライタ内蔵チップがエラーを返しました。",
        "field_message": "エラーコード2の内容をあわせて確認してください。",
        "check_points": ["エラーコード2", "対象タグ", "対象メモリバンク", "Access Password"],
    },
    0x60: {
        "category": "LBTキャリアセンス異常",
        "symbol": "CMD_LBT_ERROR",
        "technical_description": "キャリアセンス時、タイムアウトでキャリアを送信できませんでした。",
        "field_message": "周辺の電波利用状況により送信できない可能性があります。",
        "check_points": ["電波環境", "他機器", "周波数チャンネル", "再試行"],
    },
    0x64: {
        "category": "ハードウェア内部異常",
        "symbol": "HARDWARE_ERROR",
        "technical_description": "ハードウェア内部で異常が発生しました。",
        "field_message": "機器側の状態確認または保守対応が必要な可能性があります。",
        "check_points": ["電源", "再起動", "機器交換", "保守対応"],
    },
    0x68: {
        "category": "アンテナ接続異常",
        "symbol": "CMD_ANT_ERROR",
        "technical_description": "アンテナ断線検知時にRFタグ通信コマンドを送信した可能性があります。",
        "field_message": "アンテナ接続、接続チャンネル、ケーブル状態を確認してください。",
        "check_points": ["アンテナが接続されているか", "使用CHと実際の接続CHが一致しているか", "ケーブル断線や接触不良がないか", "UTRRWManagerで同じ条件を確認できるか"],
    },
    0x42: {
        "category": "コマンドSUM不一致",
        "symbol": "SUM_ERROR",
        "technical_description": "上位機器から送信されたコマンドのSUM値が不正です。",
        "field_message": "送信コマンドの生成または送信データに問題がある可能性があります。",
        "check_points": ["コマンド生成", "SUM計算", "送信データ欠落"],
    },
    0x44: {
        "category": "コマンドフォーマット不正",
        "symbol": "FORMAT_ERROR",
        "technical_description": "上位機器から送信されたコマンドのフォーマットまたはパラメータが不正です。",
        "field_message": "データ長、詳細コマンド、パラメータ範囲を確認してください。",
        "check_points": ["データ長", "詳細コマンド", "パラメータ範囲", "対象機種対応"],
    },
}


NACK_ERROR_CODE_2_INFO: dict[int, dict[str, Any]] = {
    0x01: {"symbol": "UNSUPPORTED", "technical_description": "サポートされていません", "check_points": ["コマンド種別", "対象タグ", "対象機種対応"]},
    0x02: {"symbol": "INSUFFICIENT_PRIVILEGES", "technical_description": "権限が不十分", "check_points": ["Access Password", "対象メモリバンク", "タグのロック状態"]},
    0x03: {"symbol": "MEMORY_OVERRUN", "technical_description": "メモリオーバーラン", "check_points": ["対象メモリバンク", "書き込み対象アドレス", "データ長"]},
    0x04: {"symbol": "MEMORY_LOCKED", "technical_description": "メモリロック", "check_points": ["対象バンクがロック済みでないか", "書き込み対象アドレス", "Access Password"]},
    0x05: {"symbol": "CRYPTO_SUITE_ERROR", "technical_description": "暗号違反", "check_points": ["Access Password", "対象タグ設定", "再実行"]},
    0x06: {"symbol": "COMMAND_NOT_ENCAPSULATED", "technical_description": "コマンドはカプセル化されません", "check_points": ["コマンド種別", "パラメータ", "対象タグ"]},
    0x07: {"symbol": "RESPONSE_BUFFER_OVERFLOW", "technical_description": "レスポンスバッファオーバーフロー", "check_points": ["応答データ長", "タグ枚数", "再実行"]},
    0x08: {"symbol": "SECURITY_TIMEOUT", "technical_description": "セキュリティアウト", "check_points": ["Access Password", "タグ状態", "再実行"]},
    0x0B: {"symbol": "INSUFFICIENT_POWER", "technical_description": "不十分な電力", "check_points": ["タグ距離", "タグ向き", "送信出力", "アンテナ位置"]},
    0x0F: {"symbol": "NON_SPECIFIC_ERROR", "technical_description": "非特定のエラー", "check_points": ["再実行", "タグ状態", "通信条件"]},
    0x20: {"symbol": "WRITE_FAILED", "technical_description": "Writeに失敗", "check_points": ["対象メモリバンク", "書き込み対象アドレス", "Access Password"]},
    0x22: {"symbol": "KILL_FAILED", "technical_description": "Killに失敗", "check_points": ["Kill Password", "対象タグ", "タグ状態"]},
    0x23: {"symbol": "LOCK_FAILED", "technical_description": "Lockに失敗", "check_points": ["Access Password", "対象メモリバンク", "ロック設定"]},
    0x80: {"symbol": "NOT_DETECTED", "technical_description": "検出されない", "check_points": ["タグ距離", "タグ向き", "アンテナ接続", "送信出力", "タグ種別"]},
    0x81: {"symbol": "HANDLE_ACQUISITION_FAILED", "technical_description": "ハンドル取得失敗", "check_points": ["タグ距離", "タグ応答", "再実行"]},
    0x82: {"symbol": "ACCESS_PASSWORD_ERROR", "technical_description": "Accessパスワードエラー", "check_points": ["Access Password設定", "対象メモリバンク", "タグのロック状態"]},
    0x90: {"symbol": "CRC_ERROR", "technical_description": "CRCエラー", "check_points": ["タグ距離", "タグ向き", "電波環境", "再実行"]},
}


UHF_ENCODE_ERROR_CODE_3_INFO: dict[int, dict[str, Any]] = {
    0x01: {"symbol": "RESERVED_WRITE_ERROR", "technical_description": "Reserved領域への書き込み時にエラー", "check_points": ["対象領域", "Access Password", "ロック状態"]},
    0x02: {"symbol": "EPC_UII_WRITE_ERROR", "technical_description": "EPC(UII)領域への書き込み時にエラー", "check_points": ["EPC(UII)領域", "書き込みデータ", "Access Password", "ロック状態"]},
    0x03: {"symbol": "USER_WRITE_ERROR", "technical_description": "User領域への書き込み時にエラー", "check_points": ["User領域", "書き込み対象アドレス", "Access Password", "ロック状態"]},
    0x05: {"symbol": "LOCK_COMMAND_ERROR", "technical_description": "Lockコマンド発行時にエラー", "check_points": ["Lock設定", "Access Password", "対象メモリバンク"]},
}


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


def parse_output_power_dbm(data: bytes) -> float:
    """RF送信出力レベルを dBm に変換します。

    UHF_READ_OUTPUT_POWER (`55 43 01`) のRF送信出力レベルは
    `dBm * 10` で、1バイト目がLSB、2バイト目がMSBです。

    Args:
        data: RF送信出力レベルの2バイト列。LSB、MSBの順です。

    Returns:
        dBm 単位の送信出力値。

    Raises:
        ValueError: 2バイト以外が渡された場合。
    """
    if len(data) != 2:
        raise ValueError("output power level must be exactly 2 bytes")

    return parse_little_endian_u16(data) / 10.0


def _unknown_info(code: Optional[int], label: str) -> dict[str, Any]:
    code_text = "None" if code is None else f"0x{code:02X}"
    return {
        "category": "仕様書未定義または未対応コード",
        "symbol": "UNKNOWN",
        "technical_description": f"{label} {code_text} は仕様書未定義または未対応コードです。",
        "field_message": "コード値、詳細コマンド、対象機種、実行条件を確認してください。",
        "check_points": ["コード値", "詳細コマンド", "対象機種", "実行条件"],
    }


def get_nack_error_code_1_info(code: int) -> dict[str, Any]:
    """Return UTR-S201 UHF Gen2 NACK error-code-1 information."""
    return NACK_ERROR_CODE_1_INFO.get(code, _unknown_info(code, "エラーコード1"))


def get_nack_error_code_2_info(code: int) -> dict[str, Any]:
    """Return UHF Gen2 error-code-2 information."""
    return NACK_ERROR_CODE_2_INFO.get(
        code,
        {
            "category": "RFタグアクセス処理失敗",
            "symbol": "PROCESS_FAILED",
            "technical_description": "処理失敗",
            "field_message": "エラーコード2は未定義または未対応です。",
            "check_points": ["対象タグ", "対象メモリバンク", "Access Password", "実行条件"],
        },
    )


def get_uhf_encode_error_code_3_info(code: int) -> dict[str, Any]:
    """Return UHF_Encode error-code-3 information."""
    return UHF_ENCODE_ERROR_CODE_3_INFO.get(code, _unknown_info(code, "エラーコード3"))


def parse_nack_frame(frame: bytes) -> dict[str, Any]:
    """Parse a UTR-S201 UHF Gen2 NACK response frame.

    The expected NACK data layout is:
    detail command, error code 1, error code 2, error code 3,
    error code 4, and five reserved bytes.
    """
    raw_hex = frame.hex().upper()
    result: dict[str, Any] = {
        "raw_hex": raw_hex,
        "detail_command": None,
        "error_code_1": None,
        "error_code_2": None,
        "error_code_3": None,
        "error_code_4": None,
        "category": "NACK解析エラー",
        "symbol": "INVALID_NACK_FRAME",
        "technical_description": "NACKフレームが短すぎるか、形式が不正です。",
        "field_message": "受信データ長とフレーム形式を確認してください。",
        "check_points": ["受信データ長", "STX/ETX/CR", "データ長", "Raw hex"],
        "parse_error": None,
    }

    if len(frame) < HEADER_LENGTH + FOOTER_LENGTH:
        result["parse_error"] = "NACKフレームが短すぎます。"
        return result

    if frame[0:1] != STX or frame[CMD_LOCATION:CMD_LOCATION + 1] != NACK:
        result["parse_error"] = "NACK応答フレームではありません。"
        return result

    data_length = frame[3]
    expected_length = HEADER_LENGTH + data_length + FOOTER_LENGTH
    if len(frame) < expected_length:
        result["parse_error"] = "NACKフレームがデータ長より短いです。"
        return result

    if data_length < NACK_FRAME_DATA_LENGTH:
        result["parse_error"] = "NACKデータ部が短すぎます。"
        return result

    result["detail_command"] = frame[4]
    result["error_code_1"] = frame[5]
    result["error_code_2"] = frame[6]
    result["error_code_3"] = frame[7]
    result["error_code_4"] = frame[8]

    code_1_info = get_nack_error_code_1_info(frame[5])
    result.update(
        {
            "category": code_1_info["category"],
            "symbol": code_1_info["symbol"],
            "technical_description": code_1_info["technical_description"],
            "field_message": code_1_info["field_message"],
            "check_points": code_1_info["check_points"],
            "error_code_1_info": code_1_info,
            "error_code_2_info": get_nack_error_code_2_info(frame[6]),
            "error_code_3_info": get_uhf_encode_error_code_3_info(frame[7]),
        }
    )
    return result


def format_nack_message(frame: bytes) -> list[str]:
    """Format a NACK response for field-support troubleshooting."""
    parsed = parse_nack_frame(frame)
    lines = ["NACK応答を受信しました。"]

    if parsed["detail_command"] is not None:
        lines.append(f"詳細コマンド: 0x{parsed['detail_command']:02X}")
    else:
        lines.append("詳細コマンド: 取得できません")

    if parsed["error_code_1"] is not None:
        lines.append(f"エラーコード1: 0x{parsed['error_code_1']:02X} {parsed['symbol']}")
    else:
        lines.append("エラーコード1: 取得できません")

    lines.append(f"分類: {parsed['category']}")
    lines.append(f"内容: {parsed['technical_description']}")
    lines.append(f"現場向け: {parsed['field_message']}")

    if parsed.get("parse_error"):
        lines.append(f"解析エラー: {parsed['parse_error']}")

    if parsed["error_code_1"] == 0x0A and parsed["error_code_2"] is not None:
        code_2_info = parsed["error_code_2_info"]
        lines.append(f"エラーコード2: 0x{parsed['error_code_2']:02X} {code_2_info['technical_description']}")
        lines.append("エラーコード2の確認ポイント:")
        lines.extend(f"* {point}" for point in code_2_info["check_points"])

    if parsed["error_code_3"] not in (None, 0x00):
        code_3_info = parsed["error_code_3_info"]
        lines.append(f"エラーコード3: 0x{parsed['error_code_3']:02X} {code_3_info['technical_description']}")
        lines.append("エラーコード3の確認ポイント:")
        lines.extend(f"* {point}" for point in code_3_info["check_points"])

    lines.append("確認してください:")
    lines.extend(f"* {point}" for point in parsed["check_points"])
    lines.append(f"Raw: {parsed['raw_hex']}")
    return lines


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
    parsed = parse_nack_frame(nack_response)
    error_code = parsed["error_code_1"]
    if error_code is None and len(nack_response) > 5:
        error_code = nack_response[5]
        code_1_info = get_nack_error_code_1_info(error_code)
        if code_1_info["symbol"] == "UNKNOWN":
            return f"Unknown NACK error (0x{error_code:02X})"
        return f"{code_1_info['symbol']}: {code_1_info['technical_description']}"
    if error_code is None:
        return "Invalid NACK response"
    if parsed["symbol"] == "UNKNOWN":
        return f"Unknown NACK error (0x{error_code:02X})"
    return f"{parsed['symbol']}: {parsed['technical_description']}"


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
