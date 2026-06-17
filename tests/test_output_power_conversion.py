#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""送信出力値変換ヘルパーのテスト。"""

from decimal import Decimal

import pytest

from src.utr_output_power import (
    output_power_bytes_to_dbm,
    output_power_dbm_to_bytes,
    output_power_dbm_to_raw_value,
)


def test_output_power_dbm_to_raw_value_converts_dbm_to_tenths():
    assert output_power_dbm_to_raw_value(24.0) == 240
    assert output_power_dbm_to_raw_value("10.5") == 105
    assert output_power_dbm_to_raw_value(Decimal("0.1")) == 1


def test_output_power_dbm_to_bytes_uses_little_endian_order():
    assert output_power_dbm_to_bytes(24.0) == bytes.fromhex("F0 00")
    assert output_power_dbm_to_bytes("10.5") == bytes.fromhex("69 00")
    assert output_power_dbm_to_bytes(Decimal("6553.5")) == bytes.fromhex("FF FF")


def test_output_power_bytes_to_dbm_converts_little_endian_bytes():
    assert output_power_bytes_to_dbm(bytes.fromhex("F0 00")) == 24.0
    assert output_power_bytes_to_dbm(bytes.fromhex("69 00")) == 10.5
    assert output_power_bytes_to_dbm(bytes.fromhex("FF FF")) == 6553.5


@pytest.mark.parametrize("value", ["24.05", 24.05, Decimal("24.05")])
def test_output_power_dbm_to_raw_value_rejects_non_tenth_steps(value):
    with pytest.raises(ValueError, match="0.1 dBm"):
        output_power_dbm_to_raw_value(value)


@pytest.mark.parametrize("value", [-0.1, "6553.6"])
def test_output_power_dbm_to_raw_value_rejects_values_outside_uint16_expression(value):
    with pytest.raises(ValueError, match="unsigned 16-bit"):
        output_power_dbm_to_raw_value(value)


@pytest.mark.parametrize("value", [True, False, "not-a-number", float("inf")])
def test_output_power_dbm_to_raw_value_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        output_power_dbm_to_raw_value(value)


@pytest.mark.parametrize("data", [b"", b"\xF0", b"\xF0\x00\x00"])
def test_output_power_bytes_to_dbm_rejects_invalid_byte_length(data):
    with pytest.raises(ValueError, match="exactly 2 bytes"):
        output_power_bytes_to_dbm(data)
