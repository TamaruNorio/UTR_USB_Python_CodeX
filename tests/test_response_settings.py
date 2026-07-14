import pytest

from src.utr_commands import build_frame
from src.utr_response_settings import parse_epc_uii_response_settings


def test_parse_epc_uii_response_flags():
    parsed = parse_epc_uii_response_settings(build_frame(0x30, b"\x43\x05\x01\x0D"))
    assert parsed.parameter_kind == 1
    assert parsed.epc_buffering_enabled
    assert not parsed.read_cycle_completion_enabled
    assert parsed.antenna_switch_completion_enabled
    assert parsed.carrier_detect_response_enabled


def test_parse_epc_uii_response_rejects_reserved_bits():
    with pytest.raises(ValueError):
        parse_epc_uii_response_settings(build_frame(0x30, b"\x43\x05\x00\x80"))
