from src.utr_antenna import RomVersionInfo
from src.utr_commands import build_frame
from src.utr_device_profile import DeviceProfile
from src.utr_reader_settings import FrequencySetting
from src.utr_usm02_safe_controls import choose_temporary_channel, execute_safe_controls
import pytest


def _profile():
    return DeviceProfile(
        model_key="UTR-SUN02-4CH",
        rom=RomVersionInfo("2052USM02", "2", "052", "USM02"),
        antenna_capacity=4,
        configured_antennas=(0,),
        connected_antennas=(0, 1),
        antenna_id_output_enabled=True,
    )


def _frequency_read(start=26, current=26):
    return build_frame(
        0x30,
        bytes([0x43, 0x02, 0x00, start, current, 0xC0, 0x1F, 0x00, 0, 0, 0, 0]),
    )


def _frequency_write_ack(start):
    return build_frame(
        0x30,
        bytes([0x33, 0x02, 0x00, start, 0x00, 0xC0, 0x1F, 0x00, 0, 0, 0, 0]),
    )


def test_choose_temporary_channel_prefers_permitted_26_to_32():
    setting = FrequencySetting(0, 26, 26, (5, 26, 27), b"\x41\x00\x00", b"\x00" * 4, b"")
    assert choose_temporary_channel(setting) == 27


def test_execute_safe_controls_changes_and_restores_without_rf_or_flash():
    responses = [
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
        _frequency_read(26, 26),
        build_frame(0x30, b""),
        build_frame(0x30, b"\x33\x00\x00\x80\x02\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x02\x00\x00\x00"),
        _frequency_write_ack(27),
        _frequency_read(27, 26),
        _frequency_write_ack(26),
        _frequency_read(26, 26),
        build_frame(0x30, b"\x33\x00\x00\x80\x01\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    class Serial:
        def reset_input_buffer(self):
            pass

    result = execute_safe_controls(Serial(), _profile(), exchange, target_antenna=1)

    assert result.buzzer_ack_verified
    assert result.antenna_restored
    assert result.frequency_restored
    assert result.original_starting_channel == 26
    assert result.temporary_starting_channel == 27
    assert not result.rf_transmission_executed
    assert not result.flash_write_executed

    sent_data = [frame[4:4 + frame[3]] for frame in sent]
    assert all(not (data and data[0] in {0x10, 0x17, 0x18, 0x1E, 0x6F}) for data in sent_data)
    frequency_writes = [data for data in sent_data if data[:2] == b"\x33\x02"]
    assert len(frequency_writes) == 2
    assert all(data[2] == 0x00 for data in frequency_writes)


def test_unexpected_nack_still_restores_frequency_and_antenna():
    nack = build_frame(0x31, b"\x33\x44\x00\x00\x00\x00\x00\x00\x00\x00")
    responses = [
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
        _frequency_read(26, 26),
        build_frame(0x30, b""),
        build_frame(0x30, b"\x33\x00\x00\x80\x02\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x02\x00\x00\x00"),
        nack,
        _frequency_write_ack(26),
        _frequency_read(26, 26),
        build_frame(0x30, b"\x33\x00\x00\x80\x01\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    class Serial:
        def reset_input_buffer(self):
            pass

    with pytest.raises(RuntimeError, match="NACK_OBSERVED"):
        execute_safe_controls(Serial(), _profile(), exchange, target_antenna=1)

    assert len(sent) == 10
    assert sent[-4][4:7] == b"\x33\x02\x00"
    assert sent[-2][4:7] == b"\x33\x00\x00"


def test_optional_inventory_reports_only_count_antenna_and_channel():
    inventory = (
        build_frame(0x6C, b"\x10\x00\x00\x00\x00", address=1)
        + build_frame(0x30, b"\x10\x00\x01\x00\x1B")
    )
    responses = [
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
        _frequency_read(26, 26),
        build_frame(0x30, b""),
        build_frame(0x30, b"\x33\x00\x00\x80\x02\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x02\x00\x00\x00"),
        _frequency_write_ack(27),
        _frequency_read(27, 26),
        inventory,
        _frequency_write_ack(26),
        _frequency_read(26, 27),
        build_frame(0x30, b"\x33\x00\x00\x80\x01\x00\x00\x00"),
        build_frame(0x30, b"\x43\x00\x00\x80\x01\x00\x00\x00"),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    class Serial:
        def reset_input_buffer(self):
            pass

    result = execute_safe_controls(
        Serial(),
        _profile(),
        exchange,
        target_antenna=1,
        verify_rf_channel=True,
    )

    assert result.rf_transmission_executed
    assert result.inventory_tag_response_count == 1
    assert result.observed_tag_antennas == (1,)
    assert result.observed_rf_channel == 27
    assert result.frequency_restored
    assert result.antenna_restored
    assert [frame[4:5] for frame in sent].count(b"\x10") == 1
