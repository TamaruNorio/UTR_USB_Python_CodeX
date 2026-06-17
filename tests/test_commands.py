import pytest

import src.utr_commands as commands


def test_get_command_returns_rom_version_check():
    assert commands.get_command("ROM_VERSION_CHECK") == commands.COMMANDS["ROM_VERSION_CHECK"]


def test_get_command_rejects_unknown_name():
    with pytest.raises(ValueError):
        commands.get_command("UNKNOWN_COMMAND")


def test_list_command_names_and_is_known_command():
    names = commands.list_command_names()

    assert "ROM_VERSION_CHECK" in names
    assert "UHF_INVENTORY" in names
    assert "UHF_WRITE" in names
    assert commands.is_known_command("UHF_READ_OUTPUT_POWER") is True
    assert commands.is_known_command("NOT_DEFINED") is False


def test_build_frame_matches_rom_version_check():
    frame = commands.build_frame(command_code=0x4F, data=bytes([0x90]), address=0x00)

    assert frame == commands.COMMANDS["ROM_VERSION_CHECK"]


def test_build_frame_sets_data_length():
    frame = commands.build_frame(command_code=0x55, data=bytes([0x43, 0x01, 0x00]))

    assert frame[3] == 3


def test_build_frame_rejects_address_out_of_range():
    with pytest.raises(ValueError):
        commands.build_frame(command_code=0x4F, data=b"", address=0x100)


def test_build_frame_rejects_command_code_out_of_range():
    with pytest.raises(ValueError):
        commands.build_frame(command_code=0x100, data=b"")


def test_build_frame_rejects_too_long_data():
    with pytest.raises(ValueError):
        commands.build_frame(command_code=0x4F, data=bytes(256))


def test_build_buzzer_command_matches_pi_command():
    assert commands.build_buzzer_command(response_required=True, sound_type=0x00) == commands.COMMANDS["UHF_BUZZER_pi"]


def test_build_buzzer_command_matches_pipipi_command():
    assert commands.build_buzzer_command(response_required=True, sound_type=0x01) == commands.COMMANDS["UHF_BUZZER_pipipi"]


def test_build_buzzer_command_rejects_sound_type_out_of_range():
    with pytest.raises(ValueError):
        commands.build_buzzer_command(sound_type=0x09)


def test_build_write_output_setting_command_builds_command_mode_frame():
    frame = commands.build_write_output_setting_command(
        parameter_kind=commands.PARAMETER_KIND_COMMAND_MODE,
        output_power_dbm="24.0",
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )

    assert frame == bytes.fromhex("02 00 55 0B 33 01 00 F0 00 D0 07 32 00 C8 00 03 5A 0D")


def test_build_write_output_setting_command_builds_auto_read_mode_frame():
    frame = commands.build_write_output_setting_command(
        parameter_kind=commands.PARAMETER_KIND_AUTO_READ_MODE,
        output_power_dbm="24.0",
        carrier_transmission_time_ms=2000,
        carrier_off_time_ms=50,
        carrier_sense_wait_time_ms=200,
    )

    assert frame == bytes.fromhex("02 00 55 0B 33 01 01 F0 00 D0 07 32 00 C8 00 03 5B 0D")


def test_build_write_output_setting_command_rejects_flash_parameter_kind():
    with pytest.raises(ValueError, match="FLASH"):
        commands.build_write_output_setting_command(
            parameter_kind=commands.PARAMETER_KIND_FLASH,
            output_power_dbm="24.0",
            carrier_transmission_time_ms=2000,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        )


@pytest.mark.parametrize("parameter_kind", [-1, 0x03, 0x100])
def test_build_write_output_setting_command_rejects_unsupported_parameter_kind(parameter_kind):
    with pytest.raises(ValueError, match="parameter_kind"):
        commands.build_write_output_setting_command(
            parameter_kind=parameter_kind,
            output_power_dbm="24.0",
            carrier_transmission_time_ms=2000,
            carrier_off_time_ms=50,
            carrier_sense_wait_time_ms=200,
        )


@pytest.mark.parametrize(
    "field_name, kwargs",
    [
        ("carrier_transmission_time_ms", {"carrier_transmission_time_ms": -1}),
        ("carrier_transmission_time_ms", {"carrier_transmission_time_ms": 0x10000}),
        ("carrier_off_time_ms", {"carrier_off_time_ms": -1}),
        ("carrier_off_time_ms", {"carrier_off_time_ms": 0x10000}),
        ("carrier_sense_wait_time_ms", {"carrier_sense_wait_time_ms": -1}),
        ("carrier_sense_wait_time_ms", {"carrier_sense_wait_time_ms": 0x10000}),
    ],
)
def test_build_write_output_setting_command_rejects_invalid_u16_values(field_name, kwargs):
    base_kwargs = {
        "parameter_kind": commands.PARAMETER_KIND_COMMAND_MODE,
        "output_power_dbm": "24.0",
        "carrier_transmission_time_ms": 2000,
        "carrier_off_time_ms": 50,
        "carrier_sense_wait_time_ms": 200,
    }
    base_kwargs.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        commands.build_write_output_setting_command(**base_kwargs)


def test_validate_defined_commands_all_true():
    results = commands.validate_defined_commands()

    assert results
    assert all(results.values())
