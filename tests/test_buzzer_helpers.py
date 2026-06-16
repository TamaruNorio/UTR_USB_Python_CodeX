import sys
import types


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


def test_parse_yes_no_answer_accepts_y_values():
    assert sample.parse_yes_no_answer("y", default=False) is True
    assert sample.parse_yes_no_answer("Y", default=False) is True


def test_parse_yes_no_answer_accepts_no_and_enter_as_false():
    assert sample.parse_yes_no_answer("", default=False) is False
    assert sample.parse_yes_no_answer("n", default=False) is False
    assert sample.parse_yes_no_answer("N", default=False) is False


def test_parse_yes_no_answer_returns_none_for_invalid_input():
    assert sample.parse_yes_no_answer("maybe", default=False) is None


def test_select_buzzer_command_for_detected_tag_uses_pipipi():
    assert sample.select_buzzer_command_for_inventory_result(True) == sample.COMMANDS["UHF_BUZZER_pipipi"]


def test_select_buzzer_command_for_no_tag_uses_pi():
    assert sample.select_buzzer_command_for_inventory_result(False) == sample.COMMANDS["UHF_BUZZER_pi"]
