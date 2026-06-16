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

try:
    from src.utr_protocol import CR, ETX, STX, calculate_sum_value
except ModuleNotFoundError:
    # `py .\utr_usb_sample.py` を src フォルダ内から直接実行した場合でも、
    # utr_commands.py が読み込めるようにするための互換処理です。
    from utr_protocol import CR, ETX, STX, calculate_sum_value


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

# ブザー音種別の定数です。
# 数値の意味をコード中に直接書くと、あとから見た人が判断しにくくなるため、
# タグあり、タグなし、NACK用を名前付き定数として扱います。
BUZZER_SOUND_PI = 0x00       # タグ未検出時に使う既存の「ピー」音
BUZZER_SOUND_PIPIPI = 0x01   # タグ検出時に使う既存の「ピッピッピ」音
BUZZER_SOUND_NACK = 0x02     # NACK時に使う候補音。実音は実機確認で確認します。

# リーダライタ設定コマンドで指定するパラメータ種類です。
# 0x00: コマンドモード用パラメータ、0x01: 自動読み取りモード用パラメータ、0x02: FLASHデータ。
PARAMETER_KIND_COMMAND_MODE = 0x00
PARAMETER_KIND_AUTO_READ_MODE = 0x01
PARAMETER_KIND_FLASH = 0x02


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


def build_read_antenna_switching_setting_command(parameter_kind: int = PARAMETER_KIND_COMMAND_MODE) -> bytes:
    """アンテナ切替設定の読み取りコマンドを生成します。

    Args:
        parameter_kind: 読み取るパラメータ種類。
            0x00 = コマンドモード用パラメータ
            0x01 = 自動読み取りモード用パラメータ
            0x02 = FLASHデータ

    Returns:
        送信用フレーム。

    注意:
        このコマンドはアンテナ切替設定の「読み取り」です。
        設定値の書き込みは行いません。
    """
    _validate_byte_value(parameter_kind, "parameter_kind")
    return build_frame(0x55, bytes([0x43, 0x00, parameter_kind]))


def build_check_antenna_command(antenna_number: int) -> bytes:
    """UHF_CheckAntennaコマンドを生成します。

    Args:
        antenna_number: 接続確認するアンテナ番号。
            UHF_CheckAntennaでは、4CH機は0x00〜0x03、
            8CH機は0x00〜0x07を使用します。

    Returns:
        送信用フレーム。

    重要:
        UHF_CheckAntennaのDATA部は `44h + アンテナ番号` の2バイトです。
        `44h + アンテナ番号 + 00h + 00h` ではありません。
    """
    _validate_byte_value(antenna_number, "antenna_number")
    return build_frame(0x55, bytes([0x44, antenna_number]))


def build_write_antenna_switching_setting_command(
    parameter_kind: int,
    switching_mode: int,
    antenna_id_output_enabled: bool,
    antenna_mask: int,
) -> bytes:
    """アンテナ切替設定の書き込みコマンドを生成します。

    Args:
        parameter_kind:
            書き込み先のパラメータ種類。
            今回の実機操作では 0x00 = コマンドモード用パラメータのみ使用します。
        switching_mode:
            アンテナ切替方式。現在値を保持して書き戻す用途を想定します。
        antenna_id_output_enabled:
            アンテナID出力を有効にする場合は True。
        antenna_mask:
            使用アンテナのビットマスク。
            例: Ant0=0x01, Ant1=0x02, Ant2=0x04, Ant3=0x08。

    Returns:
        送信用フレーム。

    重要:
        この関数はフレームを生成するだけです。
        実際にFLASHへ書き込むかどうかは呼び出し側が制御します。
        PR-17ではFLASHへは書き込みません。
    """
    _validate_byte_value(parameter_kind, "parameter_kind")
    _validate_byte_value(switching_mode, "switching_mode")
    _validate_byte_value(antenna_mask, "antenna_mask")

    flags = (0x80 if antenna_id_output_enabled else 0x00) | (switching_mode & 0x03)
    return build_frame(0x55, bytes([0x33, 0x00, parameter_kind, flags, antenna_mask, 0x00, 0x00, 0x00]))


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
