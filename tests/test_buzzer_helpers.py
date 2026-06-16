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

def test_select_buzzer_command_for_nack_uses_generated_nack_sound():
    # NACK時はタグ有無よりもNACKを優先し、sound_type=0x02 のブザーコマンドを使う。
    expected = sample.build_buzzer_command(
        response_required=True,
        sound_type=sample.BUZZER_SOUND_NACK,
    )

    assert sample.select_buzzer_command_for_inventory_result(False, has_nack=True) == expected
    assert sample.select_buzzer_command_for_inventory_result(True, has_nack=True) == expected


def test_get_buzzer_success_message_distinguishes_nack_from_no_tag():
    # 画面表示でも、NACKとタグ未検出を混同しないようにする。
    assert "NACK応答" in sample.get_buzzer_success_message(has_tag=False, has_nack=True)
    assert "NACK用ブザー" in sample.get_buzzer_success_message(has_tag=False, has_nack=True)
    assert "タグ未検出" in sample.get_buzzer_success_message(has_tag=False, has_nack=False)
    assert "ピッピッピ" in sample.get_buzzer_success_message(has_tag=True, has_nack=False)


def test_received_data_contains_nack_detects_antenna_error_frame():
    # 実機確認で得られたNACK応答と同じ形式のテストデータ。
    # 顧客情報や実測PC/UIIではなく、NACK制御フレームのみを使う。
    nack_frame = bytes.fromhex("0200310A1068000000000000000003B80D")

    assert sample.received_data_contains_nack(nack_frame) is True


def test_received_data_contains_nack_returns_false_without_nack():
    # NACKを含まない既存のブザーコマンドではFalseになる。
    assert sample.received_data_contains_nack(sample.COMMANDS["UHF_BUZZER_pi"]) is False


def test_should_stop_inventory_repeat_only_when_nack():
    assert sample.should_stop_inventory_repeat(True) is True
    assert sample.should_stop_inventory_repeat(False) is False
