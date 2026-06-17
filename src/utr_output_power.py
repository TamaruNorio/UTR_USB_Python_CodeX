#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力値の変換ヘルパー。

このモジュールは、送信出力値の「dBm表記」と
コマンドで使う「2バイト little-endian 値」の相互変換だけを扱います。

重要:
- USB実機通信は行いません。
- 送信出力の書き込みコマンドは生成しません。
- FLASH保存は行いません。
- 機種別の許可範囲はここでは推測しません。

仕様上の値表現:
- RF送信出力レベルは dBm * 10 の整数値です。
- 2バイト値は little-endian、つまり LSB, MSB の順です。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union

try:
    from src.utr_protocol import parse_little_endian_u16
except ModuleNotFoundError:
    from utr_protocol import parse_little_endian_u16


OutputPowerValue = Union[int, float, str, Decimal]

OUTPUT_POWER_TENTHS_PER_DBM = Decimal("10")
OUTPUT_POWER_RAW_MIN = 0
OUTPUT_POWER_RAW_MAX = 0xFFFF
OUTPUT_POWER_CANCEL_INPUTS = {"", "q", "quit", "cancel"}


def _to_decimal_dbm(value: OutputPowerValue) -> Decimal:
    """入力された送信出力値を Decimal の dBm 値へ正規化します。

    Args:
        value: dBm単位の送信出力値。例: 24.0, "24.0", Decimal("24.0")。

    Returns:
        Decimal型のdBm値。

    Raises:
        ValueError: 数値に変換できない場合、有限値でない場合、bool値の場合。
    """
    if isinstance(value, bool):
        raise ValueError("output power dBm must be a numeric value, not bool")

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("output power dBm must be numeric") from exc

    if not decimal_value.is_finite():
        raise ValueError("output power dBm must be finite")

    return decimal_value


def output_power_dbm_to_raw_value(value: OutputPowerValue) -> int:
    """dBm単位の送信出力値を、コマンド用の整数値へ変換します。

    例:
        24.0 dBm -> 240 -> 0x00F0

    注意:
        ここでは機器ごとの許可範囲は判定しません。
        仕様上の2バイト表現に収まることと、0.1 dBm単位であることだけを確認します。

    Args:
        value: dBm単位の送信出力値。

    Returns:
        dBm * 10 の整数値。

    Raises:
        ValueError: 0.1 dBm単位でない場合、2バイト表現に収まらない場合。
    """
    decimal_value = _to_decimal_dbm(value)
    raw_decimal = decimal_value * OUTPUT_POWER_TENTHS_PER_DBM

    if raw_decimal != raw_decimal.to_integral_value():
        raise ValueError("output power dBm must be in 0.1 dBm steps")

    raw_value = int(raw_decimal)
    if raw_value < OUTPUT_POWER_RAW_MIN or raw_value > OUTPUT_POWER_RAW_MAX:
        raise ValueError("output power raw value must fit in unsigned 16-bit")

    return raw_value


def output_power_dbm_to_bytes(value: OutputPowerValue) -> bytes:
    """dBm単位の送信出力値を、2バイト little-endian へ変換します。

    例:
        24.0 dBm -> b"\xF0\x00"

    Args:
        value: dBm単位の送信出力値。

    Returns:
        LSB, MSB の順に並んだ2バイト列。
    """
    raw_value = output_power_dbm_to_raw_value(value)
    return raw_value.to_bytes(2, byteorder="little", signed=False)


def output_power_bytes_to_dbm(data: bytes) -> float:
    """2バイト little-endian の送信出力値を dBm へ変換します。

    Args:
        data: RF送信出力レベルの2バイト列。LSB, MSB の順です。

    Returns:
        dBm単位の送信出力値。

    Raises:
        ValueError: 2バイト以外が渡された場合。
    """
    if len(data) != 2:
        raise ValueError("output power level must be exactly 2 bytes")

    return parse_little_endian_u16(data) / 10.0


def parse_output_power_dbm_input(user_input: str) -> Decimal | None:
    """ユーザー入力文字列を送信出力dBm値として解釈します。

    この関数は、将来のUI接続前に入力解釈だけをテスト可能にするための純粋関数です。
    実機通信、送信出力書き込み、FLASH保存は行いません。

    Args:
        user_input: ユーザーが入力した文字列。
            空文字、`q`、`quit`、`cancel` は変更中止として扱います。

    Returns:
        変更中止の場合は None。
        数値入力の場合は Decimal 型の dBm 値。

    Raises:
        ValueError: 数値でない場合、0.1 dBm単位でない場合、2バイト表現に収まらない場合。
    """
    stripped_input = user_input.strip()
    if stripped_input.lower() in OUTPUT_POWER_CANCEL_INPUTS:
        return None

    decimal_value = _to_decimal_dbm(stripped_input)
    output_power_dbm_to_raw_value(decimal_value)
    return decimal_value
