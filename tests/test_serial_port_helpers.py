from dataclasses import dataclass
import sys
import types

import src.utr_serial_ports as serial_ports


serial_module = types.ModuleType("serial")
serial_module.Serial = object
serial_module.SerialException = Exception
serial_module.EIGHTBITS = 8
serial_module.PARITY_NONE = "N"
serial_module.STOPBITS_ONE = 1
serial_tools_module = types.ModuleType("serial.tools")
serial_list_ports_module = types.ModuleType("serial.tools.list_ports")
serial_list_ports_module.comports = lambda: []
serial_tools_module.list_ports = serial_list_ports_module
serial_module.tools = serial_tools_module
sys.modules.setdefault("serial", serial_module)
sys.modules.setdefault("serial.tools", serial_tools_module)
sys.modules.setdefault("serial.tools.list_ports", serial_list_ports_module)

import src.utr_usb_sample as sample


@dataclass
class DummyPort:
    device: str
    description: str = "USB Serial Port"
    manufacturer: str | None = "TAKAYA"
    hwid: str | None = "USB VID:PID=xxxx:yyyy"


def test_format_port_info_uses_unknown_for_missing_manufacturer():
    port = DummyPort(device="COM6", manufacturer=None)

    lines = serial_ports.format_port_info(port, 0)

    assert any("manufacturer: 不明" in line for line in lines)


def test_format_port_info_uses_unknown_for_missing_hwid():
    port = DummyPort(device="COM6", hwid=None)

    lines = serial_ports.format_port_info(port, 0)

    assert any("hwid        : 不明" in line for line in lines)


def test_find_port_by_user_input_accepts_zero_index():
    ports = [DummyPort(device="COM6"), DummyPort(device="COM7")]

    assert serial_ports.find_port_by_user_input("0", ports) is ports[0]


def test_find_port_by_user_input_matches_com_name_case_insensitive():
    ports = [DummyPort(device="COM6")]

    assert serial_ports.find_port_by_user_input("COM6", ports) is ports[0]
    assert serial_ports.find_port_by_user_input("com6", ports) is ports[0]


def test_is_quit_input_accepts_lower_and_upper_q():
    assert serial_ports.is_quit_input("q") is True
    assert serial_ports.is_quit_input("Q") is True


def test_find_port_by_user_input_returns_none_for_invalid_input():
    ports = [DummyPort(device="COM6")]

    assert serial_ports.find_port_by_user_input("invalid", ports) is None
    assert serial_ports.find_port_by_user_input("9", ports) is None


def test_parse_baud_rate_input_uses_115200_for_empty_input():
    assert sample.parse_baud_rate_input("") == 115200


def test_parse_baud_rate_input_accepts_115200_and_19200():
    assert sample.parse_baud_rate_input("115200") == 115200
    assert sample.parse_baud_rate_input("19200") == 19200


def test_parse_baud_rate_input_ignores_surrounding_spaces():
    assert sample.parse_baud_rate_input(" 115200 ") == 115200


def test_parse_baud_rate_input_rejects_invalid_input():
    import pytest

    with pytest.raises(ValueError):
        sample.parse_baud_rate_input("abc")
