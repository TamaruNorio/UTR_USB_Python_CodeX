#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Inventory本体へ送信出力一時変更を組み込むための判定ヘルパーのテスト。"""

from src.utr_output_power_inventory_integration import (
    evaluate_output_power_temporary_change_availability,
    format_output_power_temporary_change_offer,
)
from src.utr_output_power_readout import OutputPowerTimingSettings


def _current_setting() -> dict:
    return {
        "output_power_dbm": 24.0,
        "timing_settings": OutputPowerTimingSettings(
            carrier_transmission_time_ms=100,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        ),
    }


def test_evaluate_output_power_temporary_change_availability_allows_utr_sun02_4ch():
    availability = evaluate_output_power_temporary_change_availability(
        "UTR-SUN02-4CH",
        _current_setting(),
    )

    assert availability.can_offer is True
    assert "提案できます" in availability.reason


def test_evaluate_output_power_temporary_change_availability_rejects_8ch_model():
    availability = evaluate_output_power_temporary_change_availability(
        "UTR-SUN02-8CH",
        _current_setting(),
    )

    assert availability.can_offer is False
    assert "UTR-SUN02-4CH" in availability.reason


def test_evaluate_output_power_temporary_change_availability_rejects_missing_current_setting():
    availability = evaluate_output_power_temporary_change_availability("UTR-SUN02-4CH", None)

    assert availability.can_offer is False
    assert "読み取れていない" in availability.reason


def test_evaluate_output_power_temporary_change_availability_rejects_missing_output_power():
    current_setting = {"timing_settings": _current_setting()["timing_settings"]}

    availability = evaluate_output_power_temporary_change_availability("UTR-SUN02-4CH", current_setting)

    assert availability.can_offer is False
    assert "現在の送信出力値" in availability.reason


def test_evaluate_output_power_temporary_change_availability_rejects_missing_timing():
    current_setting = {"output_power_dbm": 24.0, "timing_settings": None}

    availability = evaluate_output_power_temporary_change_availability("UTR-SUN02-4CH", current_setting)

    assert availability.can_offer is False
    assert "キャリア関連時間" in availability.reason


def test_format_output_power_temporary_change_offer_for_allowed_case():
    availability = evaluate_output_power_temporary_change_availability(
        "UTR-SUN02-4CH",
        _current_setting(),
    )

    lines = format_output_power_temporary_change_offer(availability)

    assert "送信出力の一時変更が可能です。" in lines
    assert "FLASHは変更しません。" in lines
    assert "Inventory終了時に元の送信出力へ戻します。" in lines


def test_format_output_power_temporary_change_offer_for_rejected_case():
    availability = evaluate_output_power_temporary_change_availability(
        "UTR-SUN02V-8CH",
        _current_setting(),
    )

    lines = format_output_power_temporary_change_offer(availability)

    assert "送信出力の一時変更は行いません。" in lines
    assert availability.reason in lines
