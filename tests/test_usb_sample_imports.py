#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""src.utr_usb_sample のimport漏れ防止テスト。"""

from types import SimpleNamespace

from src import utr_usb_sample
from src.utr_antenna import AntennaCheckTarget


def test_utr_usb_sample_imports_format_antenna_numbers():
    assert callable(utr_usb_sample.format_antenna_numbers)
    assert utr_usb_sample.format_antenna_numbers([0, 1]) == "Ant0, Ant1"

def _antenna_targets():
    return [
        AntennaCheckTarget(0, "ANT0", "内蔵アンテナ"),
        AntennaCheckTarget(1, "ANT1", "外付けアンテナ1"),
    ]


def test_parse_inventory_antenna_selection_input_supports_comma_separated_values():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "0,1")
    assert [target.number for target in selected] == [0, 1]


def test_parse_inventory_antenna_selection_input_supports_all():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "all")
    assert [target.number for target in selected] == [0, 1]


def test_parse_inventory_antenna_selection_input_removes_duplicates_but_keeps_order():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "1,1,0")
    assert [target.number for target in selected] == [1, 0]


def test_parse_inventory_antenna_selection_input_q_returns_none():
    selected = utr_usb_sample.parse_inventory_antenna_selection_input(_antenna_targets(), "q")
    assert selected is None


def test_inventory_antenna_selection_prompt_explains_q_keeps_current_setting():
    prompt = utr_usb_sample.INVENTORY_ANTENNA_SELECTION_PROMPT

    assert "終了は'q'" not in prompt
    assert "アンテナを指定しない場合は q を入力してください。" in prompt
    assert "現在のコマンドモード用アンテナ設定でInventoryを続行します。" in prompt


def test_restore_antenna_setting_safely_reports_restore_failure(monkeypatch, capsys):
    selection = SimpleNamespace(restore_setting=object())

    def fake_restore(_ser, _setting):
        return False

    monkeypatch.setattr(utr_usb_sample, "restore_command_mode_antenna_setting", fake_restore)

    utr_usb_sample.restore_antenna_setting_safely(SimpleNamespace(), selection)

    output = capsys.readouterr().out
    assert "コマンドモード用アンテナ設定の復元に失敗しました。" in output
    assert "機器側の現在設定をUTRRWManagerまたは再実行時の読み取りで確認してください。" in output


def test_restore_antenna_setting_safely_reports_restore_exception(monkeypatch, capsys):
    selection = SimpleNamespace(restore_setting=object())

    def fake_restore(_ser, _setting):
        raise RuntimeError("restore failed")

    monkeypatch.setattr(utr_usb_sample, "restore_command_mode_antenna_setting", fake_restore)

    utr_usb_sample.restore_antenna_setting_safely(SimpleNamespace(), selection)

    output = capsys.readouterr().out
    assert "コマンドモード用アンテナ設定の復元に失敗しました。" in output
    assert "復元エラー: restore failed" in output


def test_restore_antenna_setting_safely_clears_input_buffer_before_restore(monkeypatch, capsys):
    calls = []
    selection = SimpleNamespace(restore_setting=object())

    class FakeSerial:
        def reset_input_buffer(self):
            calls.append("clear")

    def fake_restore(_ser, _setting):
        calls.append("restore")
        return True

    monkeypatch.setattr(utr_usb_sample, "restore_command_mode_antenna_setting", fake_restore)

    utr_usb_sample.restore_antenna_setting_safely(FakeSerial(), selection)

    output = capsys.readouterr().out
    assert calls == ["clear", "restore"]
    assert "復元前に受信バッファをクリアしました。" in output


def test_restore_antenna_setting_safely_continues_when_buffer_clear_fails(monkeypatch, capsys):
    calls = []
    selection = SimpleNamespace(restore_setting=object())

    class FakeSerial:
        def reset_input_buffer(self):
            calls.append("clear")
            raise RuntimeError("buffer clear failed")

    def fake_restore(_ser, _setting):
        calls.append("restore")
        return True

    monkeypatch.setattr(utr_usb_sample, "restore_command_mode_antenna_setting", fake_restore)

    utr_usb_sample.restore_antenna_setting_safely(FakeSerial(), selection)

    output = capsys.readouterr().out
    assert calls == ["clear", "restore"]
    assert "復元前の受信バッファクリアに失敗しました。復元処理は継続します。" in output


def test_should_save_inventory_results_requires_inventory_execution():
    assert utr_usb_sample.should_save_inventory_results(0) is False
    assert utr_usb_sample.should_save_inventory_results(1) is True


def test_save_inventory_results_skips_when_inventory_not_run(monkeypatch, capsys):
    calls = []

    monkeypatch.setattr(utr_usb_sample, "save_results_to_file", lambda *args, **kwargs: calls.append("txt"))
    monkeypatch.setattr(utr_usb_sample, "save_results_to_csv", lambda *args, **kwargs: calls.append("csv"))
    monkeypatch.setattr(utr_usb_sample, "save_results_to_json", lambda *args, **kwargs: calls.append("json"))

    utr_usb_sample.save_inventory_results(0, 0.0, 0, {}, [])

    output = capsys.readouterr().out
    assert calls == []
    assert "Inventoryが実行されていないため、集計結果は保存しません。" in output


def test_save_inventory_results_saves_when_inventory_run_with_zero_tags(monkeypatch):
    calls = []

    monkeypatch.setattr(utr_usb_sample, "save_results_to_file", lambda *args, **kwargs: calls.append("txt"))
    monkeypatch.setattr(utr_usb_sample, "save_results_to_csv", lambda *args, **kwargs: calls.append("csv"))
    monkeypatch.setattr(utr_usb_sample, "save_results_to_json", lambda *args, **kwargs: calls.append("json"))

    utr_usb_sample.save_inventory_results(1, 0.5, 0, {}, [])

    assert calls == ["txt", "csv", "json"]


def test_finish_inventory_session_restores_saves_and_closes(monkeypatch):
    calls = []
    ser = SimpleNamespace(is_open=True)
    selection = SimpleNamespace(restore_setting=object())

    def fake_restore(_ser, _selection):
        calls.append("restore")

    def fake_save(total_iterations, total_read_time, total_read_count, pc_uii_count_dict, inventory_result_items):
        calls.append(
            (
                "save",
                total_iterations,
                total_read_time,
                total_read_count,
                pc_uii_count_dict,
                inventory_result_items,
            )
        )

    def fake_close(_ser):
        calls.append("close")

    monkeypatch.setattr(utr_usb_sample, "restore_antenna_setting_safely", fake_restore)
    monkeypatch.setattr(utr_usb_sample, "save_inventory_results", fake_save)
    monkeypatch.setattr(utr_usb_sample, "close_serial_safely", fake_close)

    utr_usb_sample.finish_inventory_session(
        ser,
        selection,
        2,
        1.5,
        1,
        {"E28011xxxxxxxxxxxxxx": 1},
        {
            ("E28011xxxxxxxxxxxxxx", 0, "ANT0", "内蔵アンテナ"): {
                "pc_uii": "E28011xxxxxxxxxxxxxx",
                "read_count": 1,
                "antenna_number": 0,
                "antenna_label": "ANT0",
                "antenna_description": "内蔵アンテナ",
            }
        },
    )

    assert calls == [
        "restore",
        (
            "save",
            2,
            1.5,
            1,
            {"E28011xxxxxxxxxxxxxx": 1},
            [
                {
                    "pc_uii": "E28011xxxxxxxxxxxxxx",
                    "read_count": 1,
                    "antenna_number": 0,
                    "antenna_label": "ANT0",
                    "antenna_description": "内蔵アンテナ",
                }
            ],
        ),
        "close",
    ]


def test_drain_serial_input_until_quiet_discards_available_bytes():
    calls = []

    class FakeSerial:
        def __init__(self):
            self.waiting_values = [3, 0]

        @property
        def in_waiting(self):
            if self.waiting_values:
                return self.waiting_values.pop(0)
            return 0

        def read(self, size):
            calls.append(size)
            return b"x" * size

    drained = utr_usb_sample.drain_serial_input_until_quiet(
        FakeSerial(),
        quiet_seconds=0.0,
        max_seconds=0.5,
    )

    assert drained == 3
    assert calls == [3]
