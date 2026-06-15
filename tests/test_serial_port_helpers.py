from dataclasses import dataclass

import src.utr_serial_ports as serial_ports


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
