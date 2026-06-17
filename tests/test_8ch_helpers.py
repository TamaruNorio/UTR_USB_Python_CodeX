#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向け補助関数のテスト。"""

from src.utr_8ch import format_8ch_diagnostic_notes, is_8ch_model_key


def test_is_8ch_model_key_accepts_8ch_models():
    assert is_8ch_model_key("UTR-SUN02V-8CH") is True
    assert is_8ch_model_key("UTR-SUN02-8CH") is True


def test_is_8ch_model_key_rejects_non_8ch_models():
    assert is_8ch_model_key("UTR-SUN02-4CH") is False
    assert is_8ch_model_key("UTR-S201") is False
    assert is_8ch_model_key(None) is False


def test_format_8ch_diagnostic_notes_for_sun02_8ch():
    lines = format_8ch_diagnostic_notes("UTR-SUN02-8CH")

    assert any("UTR-SUN02-8CH" in line for line in lines)
    assert any("00h〜07h" in line for line in lines)
    assert any("ANT8=E0h" in line for line in lines)
    assert any("FLASHは変更しません" in line for line in lines)


def test_format_8ch_diagnostic_notes_for_sun02v_8ch():
    lines = format_8ch_diagnostic_notes("UTR-SUN02V-8CH")

    assert any("UTR-SUN02V-8CH" in line for line in lines)
    assert any("00h〜07h" in line for line in lines)
    assert any("内部アンテナ番号×32" in line for line in lines)
    assert any("FLASHは変更しません" in line for line in lines)


def test_format_8ch_diagnostic_notes_for_non_8ch_model():
    assert format_8ch_diagnostic_notes("UTR-SUN02-4CH") == [
        "8CH機ではないため、8CH専用診断は実行しません。",
    ]
