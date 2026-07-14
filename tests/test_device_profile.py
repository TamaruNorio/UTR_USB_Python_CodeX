import pytest

from src.utr_antenna import AntennaSwitchingSetting, RomVersionInfo
from src.utr_device_profile import DeviceProfile, build_usm02_device_profile


def _rom(series="USM02", minor="052"):
    return RomVersionInfo(raw_text=f"2{minor}{series}", major_version="2", minor_version=minor, series_name=series)


def _antenna_setting(mask=0x05, antenna_id=True):
    return AntennaSwitchingSetting(
        parameter_kind=0,
        switching_mode=0,
        antenna_id_output_enabled=antenna_id,
        antenna_mask=mask,
        reserved=b"\x00\x00\x00",
        raw=b"",
    )


def test_profile_keeps_capacity_configured_and_connected_counts_separate():
    profile = build_usm02_device_profile(_rom(), _antenna_setting(), [0, 2, 3])
    assert profile.rom_number == 2052
    assert profile.antenna_capacity == 4
    assert profile.configured_antennas == (0, 2)
    assert profile.connected_antennas == (0, 2, 3)


def test_profile_rejects_non_usm02_or_out_of_range_antenna():
    with pytest.raises(ValueError):
        DeviceProfile("UTR-S201", _rom(series="USM01"), antenna_capacity=4).validate()
    with pytest.raises(ValueError):
        build_usm02_device_profile(_rom(), _antenna_setting(), [4])
