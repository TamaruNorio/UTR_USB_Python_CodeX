import pytest

from src.utr_commands import (
    PARAMETER_KIND_AUTO_READ_MODE,
    PARAMETER_KIND_COMMAND_MODE,
    PARAMETER_KIND_FLASH,
    build_read_frequency_setting_command,
    build_write_frequency_setting_command,
)


def test_build_read_frequency_setting_command_for_command_mode():
    assert build_read_frequency_setting_command(PARAMETER_KIND_COMMAND_MODE) == bytes.fromhex(
        "02 00 55 03 43 02 00 03 A2 0D"
    )


def test_build_write_frequency_preserves_enabled_mask_and_changes_start_only():
    frame = build_write_frequency_setting_command(
        PARAMETER_KIND_COMMAND_MODE,
        27,
        (26, 27, 28, 29, 30, 31, 32),
    )
    assert frame == bytes.fromhex(
        "02 00 55 0C 33 02 00 1B 00 C0 1F 00 00 00 00 00 03 95 0D"
    )


@pytest.mark.parametrize("parameter_kind", [PARAMETER_KIND_AUTO_READ_MODE, PARAMETER_KIND_FLASH])
def test_write_frequency_rejects_non_command_mode_targets(parameter_kind):
    with pytest.raises(ValueError, match="command-mode"):
        build_write_frequency_setting_command(parameter_kind, 27, (26, 27))


def test_write_frequency_requires_start_channel_to_be_enabled():
    with pytest.raises(ValueError, match="included"):
        build_write_frequency_setting_command(PARAMETER_KIND_COMMAND_MODE, 27, (26, 28))
