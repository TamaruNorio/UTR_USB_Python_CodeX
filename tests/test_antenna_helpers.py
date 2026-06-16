#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""アンテナプロトコル関連ヘルパーのテスト。"""

import pytest

from src.utr_antenna import (
    CHECK_STATUS_CONNECTION_ERROR,
    CHECK_STATUS_OK,
    CHECK_STATUS_PARAMETER_ERROR,
    antenna_mask_to_numbers,
    format_antenna_numbers,
    format_antenna_switching_setting,
    format_check_antenna_result,
    format_rom_version_info,
    get_model_profile,
    identify_model_key_from_rom,
    parse_antenna_switching_setting_response,
    parse_antenna_switching_setting_write_response,
    parse_check_antenna_response,
    parse_rom_version_response,
)
from src.utr_commands import (
    PARAMETER_KIND_COMMAND_MODE,
    PARAMETER_KIND_FLASH,
    build_check_antenna_command,
    build_read_antenna_switching_setting_command,
    build_write_antenna_switching_setting_command,
)


def test_build_read_antenna_switching_setting_command_for_command_mode():
    assert build_read_antenna_switching_setting_command(PARAMETER_KIND_COMMAND_MODE) == bytes.fromhex(
        "02 00 55 03 43 00 00 03 A0 0D"
    )


def test_build_read_antenna_switching_setting_command_for_flash():
    assert build_read_antenna_switching_setting_command(PARAMETER_KIND_FLASH) == bytes.fromhex(
        "02 00 55 03 43 00 02 03 A2 0D"
    )


def test_build_check_antenna_command_matches_real_log_for_ant0():
    assert build_check_antenna_command(0) == bytes.fromhex(
        "02 00 55 02 44 00 03 A0 0D"
    )


def test_build_check_antenna_command_matches_real_log_for_ant5():
    assert build_check_antenna_command(5) == bytes.fromhex(
        "02 00 55 02 44 05 03 A5 0D"
    )


def test_build_check_antenna_command_rejects_out_of_range():
    with pytest.raises(ValueError):
        build_check_antenna_command(256)


def test_parse_check_antenna_response_ok_from_real_log():
    response = bytes.fromhex("02 00 30 03 44 00 00 03 7C 0D")
    result = parse_check_antenna_response(response)

    assert result.antenna_number == 0
    assert result.status_code == CHECK_STATUS_OK
    assert result.is_connected is True
    assert result.status_label == "接続OK"


def test_parse_check_antenna_response_connection_error_from_real_log():
    response = bytes.fromhex("02 00 30 03 44 01 01 03 7E 0D")
    result = parse_check_antenna_response(response)

    assert result.antenna_number == 1
    assert result.status_code == CHECK_STATUS_CONNECTION_ERROR
    assert result.is_connected is False
    assert result.status_label == "接続エラー"


def test_parse_check_antenna_response_parameter_error_from_real_log():
    response = bytes.fromhex("02 00 30 03 44 05 02 03 83 0D")
    result = parse_check_antenna_response(response)

    assert result.antenna_number == 5
    assert result.status_code == CHECK_STATUS_PARAMETER_ERROR
    assert result.is_connected is False
    assert "パラメータ異常" in result.status_label


def test_parse_antenna_switching_setting_response_81_01_from_real_log():
    response = bytes.fromhex("02 00 30 08 43 00 00 81 01 00 00 00 03 02 0D")
    setting = parse_antenna_switching_setting_response(response)

    assert setting.parameter_kind == PARAMETER_KIND_COMMAND_MODE
    assert setting.switching_mode == 1
    assert setting.switching_mode_label == "制御する"
    assert setting.antenna_id_output_enabled is True
    assert setting.antenna_mask == 0x01
    assert setting.enabled_antennas == [0]


def test_parse_antenna_switching_setting_response_80_04():
    response = bytes.fromhex("02 00 30 08 43 00 00 80 04 00 00 00 03 04 0D")
    setting = parse_antenna_switching_setting_response(response)

    assert setting.parameter_kind == PARAMETER_KIND_COMMAND_MODE
    assert setting.switching_mode == 0
    assert setting.switching_mode_label == "制御しない"
    assert setting.antenna_id_output_enabled is True
    assert setting.antenna_mask == 0x04
    assert setting.enabled_antennas == [2]


def test_format_antenna_switching_setting_contains_japanese_labels():
    response = bytes.fromhex("02 00 30 08 43 00 00 81 01 00 00 00 03 02 0D")
    setting = parse_antenna_switching_setting_response(response)
    text = "\n".join(format_antenna_switching_setting(setting))

    assert "コマンドモード用パラメータ" in text
    assert "制御する" in text
    assert "アンテナID出力: 有効" in text
    assert "Ant0" in text


def test_4ch_profile_distinguishes_internal_and_external_antennas():
    profile = get_model_profile("UTR-SUN02-4CH")

    assert profile.check_targets[0].number == 0
    assert profile.check_targets[0].label == "ANT0"
    assert profile.check_targets[0].description == "内蔵アンテナ"
    assert profile.check_targets[1].label == "ANT1"
    assert profile.check_targets[1].description == "外付けアンテナ1"
    assert len(profile.check_targets) == 4


def test_8ch_profile_uses_checkantenna_numbers_00_to_07():
    profile = get_model_profile("UTR-SUN02-8CH")

    assert [target.number for target in profile.check_targets] == list(range(8))
    assert profile.check_targets[0].label == "ANT1"
    assert profile.check_targets[7].label == "ANT8"


def test_sun02v_8ch_profile_note_mentions_internal_external_rule():
    profile = get_model_profile("UTR-SUN02V-8CH")

    assert "内部アンテナ番号" in profile.note
    assert "外部アンテナ番号" in profile.note


def test_format_check_antenna_result_with_profile():
    profile = get_model_profile("UTR-SUN02-4CH")
    response = bytes.fromhex("02 00 30 03 44 00 00 03 7C 0D")
    result = parse_check_antenna_response(response)

    assert format_check_antenna_result(result, profile=profile) == "ANT0（内蔵アンテナ）: 接続OK"


def test_antenna_mask_to_numbers_and_format():
    assert antenna_mask_to_numbers(0x0F) == [0, 1, 2, 3]
    assert antenna_mask_to_numbers(0x05) == [0, 2]
    assert format_antenna_numbers([0, 2]) == "Ant0, Ant2"
    assert format_antenna_numbers([]) == "なし"

def test_parse_rom_version_response_from_real_log():
    response = bytes.fromhex("02 00 30 0A 90 32 30 35 32 55 53 4D 30 32 03 EF 0D")
    rom_info = parse_rom_version_response(response)

    assert rom_info.raw_text == "2052USM02"
    assert rom_info.major_version == "2"
    assert rom_info.minor_version == "052"
    assert rom_info.firmware_version == "2.052"
    assert rom_info.series_name == "USM02"


def test_identify_model_key_from_rom_usm02_by_spec():
    response = bytes.fromhex("02 00 30 0A 90 32 30 35 32 55 53 4D 30 32 03 EF 0D")
    rom_info = parse_rom_version_response(response)

    assert identify_model_key_from_rom(rom_info) == "UTR-SUN02-4CH"


def test_format_rom_version_info_contains_identified_model():
    response = bytes.fromhex("02 00 30 0A 90 32 30 35 32 55 53 4D 30 32 03 EF 0D")
    rom_info = parse_rom_version_response(response)
    identified_model_key = identify_model_key_from_rom(rom_info)
    text = "\n".join(format_rom_version_info(rom_info, identified_model_key=identified_model_key))

    assert "ROMバージョン: 2052USM02" in text
    assert "ファームウェアバージョン: 2.052" in text
    assert "ROMシリーズ名: USM02" in text
    assert "仕様書照合機種" in text
    assert "UTR-SUN02-4CH" in text

def test_build_write_antenna_switching_setting_command_for_command_mode_ant0():
    assert build_write_antenna_switching_setting_command(
        parameter_kind=PARAMETER_KIND_COMMAND_MODE,
        switching_mode=1,
        antenna_id_output_enabled=True,
        antenna_mask=0x01,
    ) == bytes.fromhex("02 00 55 08 33 00 00 81 01 00 00 00 03 17 0D")


def test_build_write_antenna_switching_setting_command_for_command_mode_ant1():
    assert build_write_antenna_switching_setting_command(
        parameter_kind=PARAMETER_KIND_COMMAND_MODE,
        switching_mode=1,
        antenna_id_output_enabled=True,
        antenna_mask=0x02,
    ) == bytes.fromhex("02 00 55 08 33 00 00 81 02 00 00 00 03 18 0D")


def test_build_write_antenna_switching_setting_command_for_flash_example_is_known_but_not_used_by_pr17():
    assert build_write_antenna_switching_setting_command(
        parameter_kind=PARAMETER_KIND_FLASH,
        switching_mode=1,
        antenna_id_output_enabled=True,
        antenna_mask=0x0F,
    ) == bytes.fromhex("02 00 55 08 33 00 02 81 0F 00 00 00 03 27 0D")


def test_parse_antenna_switching_setting_write_response_for_command_mode_ant0():
    response = bytes.fromhex("02 00 30 08 33 00 00 81 01 00 00 00 03 F2 0D")
    setting = parse_antenna_switching_setting_write_response(response)

    assert setting.parameter_kind == PARAMETER_KIND_COMMAND_MODE
    assert setting.switching_mode == 1
    assert setting.antenna_id_output_enabled is True
    assert setting.antenna_mask == 0x01
    assert setting.enabled_antennas == [0]


def test_parse_antenna_switching_setting_write_response_for_command_mode_ant1():
    response = bytes.fromhex("02 00 30 08 33 00 00 81 02 00 00 00 03 F3 0D")
    setting = parse_antenna_switching_setting_write_response(response)

    assert setting.parameter_kind == PARAMETER_KIND_COMMAND_MODE
    assert setting.switching_mode == 1
    assert setting.antenna_id_output_enabled is True
    assert setting.antenna_mask == 0x02
    assert setting.enabled_antennas == [1]

