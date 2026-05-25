#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USBサンプルで使うコマンド定義と生成ヘルパー。

このモジュールは、コマンドのbytes定義と、実機通信を伴わない
フレーム生成だけを扱います。

重要:
- USB実機通信は行いません。
- pyserial は import しません。
- COMポート選択、ユーザー入力、画面表示は行いません。
"""

from src.utr_protocol import CR, ETX, STX, calculate_sum_value


# src/utr_usb_sample.py の COMMANDS を安全に複製した固定コマンドです。
# 値は既存サンプルと合わせるため、ここでは意味を推測して変更しません。
COMMANDS: dict[str, bytes] = {
    "ROM_VERSION_CHECK": bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03, 0xE5, 0x0D]),
    "COMMAND_MODE_SET": bytes([0x02, 0x00, 0x4E, 0x07, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x03, 0x6A, 0x0D]),
    "UHF_INVENTORY": bytes([0x02, 0x00, 0x55, 0x01, 0x10, 0x03, 0x6B, 0x0D]),
    "UHF_GET_INVENTORY_PARAM": bytes([0x02, 0x00, 0x55, 0x02, 0x41, 0x00, 0x03, 0x9D, 0x0D]),
    "UHF_SET_INVENTORY_PARAM": bytes([0x02, 0x00, 0x55, 0x09, 0x30, 0x00, 0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x14, 0x0D]),
    "UHF_READ_OUTPUT_POWER": bytes([0x02, 0x00, 0x55, 0x03, 0x43, 0x01, 0x00, 0x03, 0xA1, 0x0D]),
    "UHF_READ_FREQ_CH": bytes([0x02, 0x00, 0x55, 0x03, 0x43, 0x02, 0x00, 0x03, 0xA2, 0x0D]),
    "UHF_BUZZER_pi": bytes([0x02, 0x00, 0x42, 0x02, 0x01, 0x00, 0x03, 0x4A, 0x0D]),
    "UHF_BUZZER_pipipi": bytes([0x02, 0x00, 0x42, 0x02, 0x01, 0x01, 0x03, 0x4B, 0x0D]),
    "UHF_WRITE": bytes([0x02, 0x00, 0x55, 0x08, 0x16, 0x01, 0x00, 0x00, 0x00, 0x02, 0x04, 0x56, 0x03, 0xD5, 0x0D]),
}


def get_command(command_name: str) -> bytes:
    """コマンド名から固定コマンドbytesを取得します。

    Args:
        command_name: `COMMANDS` に定義されているコマンド名。

    Returns:
        コマンドのbytes。

    Raises:
        ValueError: 未定義のコマンド名が指定された場合。
    """
    if command_name not in COMMANDS:
        raise ValueError(f"Unknown command: {command_name}")
    return COMMANDS[command_name]


def list_command_names() -> list[str]:
    """定義済みコマンド名の一覧を返します。"""
    return list(COMMANDS.keys())


def is_known_command(command_name: str) -> bool:
    """指定されたコマンド名が定義済みかどうかを返します。"""
    return command_name in COMMANDS


def _validate_byte_value(value: int, name: str) -> None:
    """1バイト値として扱える範囲か確認します。"""
    if not 0x00 <= value <= 0xFF:
        raise ValueError(f"{name} must be in range 0x00-0xFF")


def build_frame(command_code: int, data: bytes, address: int = 0x00) -> bytes:
    """UTR通信フレームを生成します。

    生成形式は `STX + address + command_code + data長 + data + ETX + SUM + CR` です。
    SUMは `src.utr_protocol.calculate_sum_value` で計算します。

    Args:
        command_code: コマンドコード。0x00から0xFFまで。
        data: データ部。0から255バイトまで。
        address: アドレス。0x00から0xFFまで。

    Returns:
        生成したフレームbytes。

    Raises:
        ValueError: address、command_code、data長が範囲外の場合。
    """
    _validate_byte_value(address, "address")
    _validate_byte_value(command_code, "command_code")
    if len(data) > 0xFF:
        raise ValueError("data length must be in range 0-255 bytes")

    frame_without_sum_cr = (
        STX
        + bytes([address])
        + bytes([command_code])
        + bytes([len(data)])
        + data
        + ETX
    )
    sum_value = calculate_sum_value(frame_without_sum_cr)
    return frame_without_sum_cr + bytes([sum_value]) + CR


def build_buzzer_command(response_required: bool = True, sound_type: int = 0x00) -> bytes:
    """ブザー制御コマンドを生成します。

    現行サンプルのブザーコマンドに合わせ、command_code は 0x42、
    データ部は `[response_required, sound_type]` とします。

    Args:
        response_required: 応答要求ありならTrue、なしならFalse。
        sound_type: ブザー音種別。0x00から0x08まで。

    Returns:
        生成したブザー制御フレーム。

    Raises:
        ValueError: sound_type が範囲外の場合。
    """
    if not 0x00 <= sound_type <= 0x08:
        raise ValueError("sound_type must be in range 0x00-0x08")

    response_value = 0x01 if response_required else 0x00
    return build_frame(0x42, bytes([response_value, sound_type]))


def validate_defined_commands() -> dict[str, bool]:
    """定義済みコマンドの基本的なフレーム整合性を検証します。

    STX、ETX、CR、データ長、SUMを確認します。
    コマンド仕様そのものの正しさまでは判断しません。

    Returns:
        コマンド名ごとの検証結果。
    """
    results: dict[str, bool] = {}
    for name, frame in COMMANDS.items():
        is_valid = True
        if len(frame) < 7:
            is_valid = False
        elif frame[0:1] != STX or frame[-1:] != CR:
            is_valid = False
        else:
            data_length = frame[3]
            expected_length = 4 + data_length + 3
            etx_index = 4 + data_length
            if len(frame) != expected_length:
                is_valid = False
            elif frame[etx_index:etx_index + 1] != ETX:
                is_valid = False
            elif calculate_sum_value(frame[:-2]) != frame[-2]:
                is_valid = False
        results[name] = is_valid
    return results
