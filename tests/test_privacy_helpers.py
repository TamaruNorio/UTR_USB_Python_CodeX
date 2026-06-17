#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""実機ログ・結果ファイル向けマスク補助関数のテスト。"""

import pytest

from src.utr_privacy import build_masked_pc_uii_id, get_or_create_masked_pc_uii_id


def test_build_masked_pc_uii_id_uses_three_digit_sequence():
    assert build_masked_pc_uii_id(1) == "MASKED_PC_UII_001"
    assert build_masked_pc_uii_id(12) == "MASKED_PC_UII_012"
    assert build_masked_pc_uii_id(123) == "MASKED_PC_UII_123"


def test_build_masked_pc_uii_id_rejects_non_positive_index():
    with pytest.raises(ValueError, match="1 or greater"):
        build_masked_pc_uii_id(0)


def test_get_or_create_masked_pc_uii_id_reuses_same_alias_for_same_value():
    mask_map: dict[str, str] = {}

    first = get_or_create_masked_pc_uii_id("3000AAA", mask_map)
    second = get_or_create_masked_pc_uii_id("3000BBB", mask_map)
    first_again = get_or_create_masked_pc_uii_id("3000AAA", mask_map)

    assert first == "MASKED_PC_UII_001"
    assert second == "MASKED_PC_UII_002"
    assert first_again == first
    assert mask_map == {
        "3000AAA": "MASKED_PC_UII_001",
        "3000BBB": "MASKED_PC_UII_002",
    }
