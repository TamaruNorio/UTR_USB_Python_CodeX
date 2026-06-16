#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""src.utr_usb_sample のimport漏れ防止テスト。"""

from src import utr_usb_sample


def test_utr_usb_sample_imports_format_antenna_numbers():
    assert callable(utr_usb_sample.format_antenna_numbers)
    assert utr_usb_sample.format_antenna_numbers([0, 1]) == "Ant0, Ant1"
