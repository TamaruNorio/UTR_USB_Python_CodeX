from dataclasses import replace

import pytest

from src.utr_antenna import RomVersionInfo
from src.utr_commands import build_frame
from src.utr_device_profile import DeviceProfile
from src.utr_usm02_inventory_buzzer import (
    execute_sequential_inventory_buzzer,
    normalize_target_antennas,
)
from src.utr_usm02_inventory_buzzer_cli import parse_antenna_list


def _profile() -> DeviceProfile:
    return DeviceProfile(
        model_key="UTR-SUN02-4CH",
        rom=RomVersionInfo("2052USM02", "2", "052", "USM02"),
        antenna_capacity=4,
        configured_antennas=(0,),
        connected_antennas=(0, 1, 2),
        antenna_id_output_enabled=True,
        epc_buffering_enabled=False,
    )


def _antenna_read(mask: int) -> bytes:
    return build_frame(0x30, bytes([0x43, 0x00, 0x00, 0x80, mask, 0, 0, 0]))


def _antenna_write(mask: int) -> bytes:
    return build_frame(0x30, bytes([0x33, 0x00, 0x00, 0x80, mask, 0, 0, 0]))


def _inventory(antenna: int, tag_suffix: int, *, channel: int = 26) -> bytes:
    tag = build_frame(
        0x6C,
        bytes([0x10, 0x00, 0x00, 0x00, 0x02, 0xAA, tag_suffix]),
        address=antenna,
    )
    completion = build_frame(0x30, bytes([0x10, 0x00, 0x01, 0x00, channel]))
    return tag + completion


def test_parse_and_normalize_antennas():
    assert parse_antenna_list("0, 1,2") == (0, 1, 2)
    assert normalize_target_antennas((0, 1, 2), 4) == (0, 1, 2)
    with pytest.raises(ValueError, match="重複"):
        normalize_target_antennas((0, 1, 1), 4)
    with pytest.raises(ValueError, match="物理容量外"):
        normalize_target_antennas((0, 4), 4)


def test_tag_on_each_antenna_triggers_buzzer_and_restores_without_identifier_output():
    responses = [
        _antenna_read(0x01),
        _inventory(0, 0x01),
        build_frame(0x30, b""),
        _antenna_write(0x02),
        _antenna_read(0x02),
        _inventory(1, 0x02),
        build_frame(0x30, b""),
        _antenna_write(0x04),
        _antenna_read(0x04),
        _inventory(2, 0x03),
        build_frame(0x30, b""),
        _antenna_write(0x01),
        _antenna_read(0x01),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    class Serial:
        def reset_input_buffer(self):
            pass

    result = execute_sequential_inventory_buzzer(Serial(), _profile(), exchange)

    assert result.requested_antennas == (0, 1, 2)
    assert result.inventory_execution_count == 3
    assert result.buzzer_ack_count == 3
    assert result.antenna_restored
    assert all(item.tag_detected for item in result.antenna_results)
    assert all(item.unique_tag_count == 1 for item in result.antenna_results)
    assert all(item.response_count_matches_completion for item in result.antenna_results)
    assert not result.flash_write_executed
    assert not result.tag_memory_write_executed

    sent_data = [frame[4:4 + frame[3]] for frame in sent]
    assert sent_data.count(b"\x10") == 3
    assert sum(data == b"\x01\x01" for data in sent_data) == 3
    assert all(not (data and data[0] in {0x17, 0x18, 0x1E, 0x6F}) for data in sent_data)
    serialized = str(result.to_dict())
    assert "AA01" not in serialized
    assert "AA02" not in serialized
    assert "AA03" not in serialized


def test_zero_tag_response_does_not_send_buzzer():
    responses = [
        _antenna_read(0x01),
        build_frame(0x30, b"\x10\x00\x00\x00\x1A"),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    result = execute_sequential_inventory_buzzer(object(), _profile(), exchange, target_antennas=(0,))

    item = result.antenna_results[0]
    assert not item.tag_detected
    assert item.tag_response_count == 0
    assert item.unique_tag_count == 0
    assert not item.buzzer_command_sent
    assert not item.buzzer_ack_verified
    assert len(sent) == 2


def test_missing_ant2_stops_before_any_exchange():
    profile = replace(_profile(), connected_antennas=(0, 1))
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return b""

    with pytest.raises(ValueError, match="ANT2"):
        execute_sequential_inventory_buzzer(object(), profile, exchange)

    assert sent == []


def test_epc_buffering_must_be_confirmed_off_before_any_exchange():
    profile = replace(_profile(), epc_buffering_enabled=True)
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return b""

    with pytest.raises(ValueError, match="EPCバッファリング"):
        execute_sequential_inventory_buzzer(object(), profile, exchange)

    assert sent == []


def test_timeout_after_switch_still_restores_original_antenna():
    responses = [
        _antenna_read(0x01),
        build_frame(0x30, b"\x10\x00\x00\x00\x1A"),
        _antenna_write(0x02),
        _antenna_read(0x02),
        b"",
        _antenna_write(0x01),
        _antenna_read(0x01),
    ]
    sent: list[bytes] = []

    def exchange(_ser, command):
        sent.append(command)
        return responses[len(sent) - 1]

    class Serial:
        def reset_input_buffer(self):
            pass

    with pytest.raises(RuntimeError, match="FAILED_NEEDS_ANALYSIS"):
        execute_sequential_inventory_buzzer(
            Serial(),
            _profile(),
            exchange,
            target_antennas=(0, 1),
        )

    assert sent[-2][4:9] == b"\x33\x00\x00\x80\x01"
    assert sent[-1][4:7] == b"\x43\x00\x00"
