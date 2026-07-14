import sys
from types import SimpleNamespace

from src.utr_commands import build_frame
from src import utr_usb_sample_legacy
from src.utr_usm02_v117_validation_cli import _execute_bootstrap


class _FakeSerial:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass


def test_bootstrap_only_sends_prerequisite_commands_and_builds_profile(monkeypatch):
    responses = [
        build_frame(0x30, b"\x90" + b"2052USM02"),
        build_frame(0x30, b""),
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
        build_frame(0x30, b"\x44\x00\x00"),
        build_frame(0x30, b"\x44\x01\x01"),
        build_frame(0x30, b"\x44\x02\x00"),
        build_frame(0x30, b"\x44\x03\x01"),
        build_frame(0x30, b"\x41\x00\x1F\xDC\x81\x06\x00\x00\x00\x00\x02"),
        build_frame(0x30, b"\x43\x05\x00\x01"),
        build_frame(0x30, b"\x43\x05\x01\x0E"),
    ]
    sent: list[bytes] = []

    def fake_communicate(_ser, command, timeout=1.0):
        sent.append(command)
        return responses[len(sent) - 1]

    monkeypatch.setattr(utr_usb_sample_legacy, "communicate", fake_communicate)
    monkeypatch.setitem(sys.modules, "serial", SimpleNamespace(Serial=lambda **kwargs: _FakeSerial()))

    profile = _execute_bootstrap("COM6", 115200)

    assert len(sent) == 10
    assert profile.rom.raw_text == "2052USM02"
    assert profile.configured_antennas == (0,)
    assert profile.connected_antennas == (0, 2)
    assert profile.inventory_tid_enabled
    assert profile.epc_buffering_enabled
    assert profile.read_cycle_completion_enabled
    assert profile.antenna_switch_completion_enabled
    assert profile.carrier_detect_response_enabled

    sent_data = [frame[4:4 + frame[3]] for frame in sent]
    assert b"\x6F" not in sent_data
    assert all(not (data and data[0] in {0x17, 0x18, 0x1E}) for data in sent_data)
