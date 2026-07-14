from src.utr_antenna import RomVersionInfo
from src.utr_commands import build_frame
from src.utr_device_profile import DeviceProfile
from src.utr_response_v117 import (
    AddressRole,
    FrameKind,
    VerificationResult,
    interpret_address,
    parse_frame,
    split_frames,
    verify_command_response,
)
from src.utr_v117_catalog import get_command_spec


def _profile(antenna_id=True):
    return DeviceProfile(
        model_key="UTR-SUN02-4CH",
        rom=RomVersionInfo("2052USM02", "2", "052", "USM02"),
        antenna_capacity=4,
        configured_antennas=(0,),
        connected_antennas=(0, 1),
        antenna_id_output_enabled=antenna_id,
    )


def test_parse_and_split_frames_verify_sum_and_structure():
    first = build_frame(0x30, b"\x80\x00\x00\x00")
    second = build_frame(0x30, b"\x6F")
    frames = split_frames(first + second)
    assert [frame.kind for frame in frames] == [FrameKind.ACK, FrameKind.ACK]
    broken = bytearray(first)
    broken[-2] ^= 0x01
    try:
        parse_frame(bytes(broken))
    except ValueError as exc:
        assert "SUM" in str(exc)
    else:
        raise AssertionError("SUM不一致を受理してはいけません")


def test_tag_response_address_depends_on_antenna_id_setting():
    frame = parse_frame(build_frame(0x6C, b"\x10\x00\x00\x00\x00", address=2))
    assert interpret_address(frame, _profile(True)).role == AddressRole.ANTENNA_NUMBER
    assert interpret_address(frame, _profile(False)).role == AddressRole.READER_ID


def test_fixed_ack_and_no_response_are_different_results():
    ack = build_frame(0x30, b"\x80\x00\x00\x00")
    result = verify_command_response(get_command_spec("7.3.1"), ack, _profile())
    assert result.result == VerificationResult.ACK_VERIFIED
    restart = verify_command_response(get_command_spec("7.3.10"), b"", _profile())
    assert restart.result == VerificationResult.NO_RESPONSE_VERIFIED


def test_conditional_buzzer_no_response_requires_response_flag_off():
    spec = get_command_spec("7.3.2")
    assert verify_command_response(spec, b"", _profile(), response_requested=False).result == VerificationResult.CONDITIONAL_NO_RESPONSE_VERIFIED
    assert verify_command_response(spec, b"", _profile(), response_requested=True).result == VerificationResult.FAILED_NEEDS_ANALYSIS


def test_inventory_accepts_zero_or_more_tag_frames_then_completion_ack():
    tag = build_frame(0x6C, b"\x10\x00\x00\x00\x00", address=1)
    completion = build_frame(0x30, b"\x10\x00\x00\x00\x00")
    result = verify_command_response(get_command_spec("7.5.1"), tag + completion, _profile())
    assert result.result == VerificationResult.MULTI_RESPONSE_VERIFIED
    assert "タグ応答=1件" in result.notes[-1]


def test_nack_is_parsed_but_not_counted_as_ack_success():
    nack_data = b"\x15\x04\x00\x00\x00\x00\x00\x00\x00\x00"
    result = verify_command_response(get_command_spec("7.5.3"), build_frame(0x31, nack_data), _profile())
    assert result.result == VerificationResult.NACK_OBSERVED
    assert result.nack["error_code_1"] == 0x04


def test_wrong_subcommand_and_wrong_length_fail():
    wrong_sub = build_frame(0x30, b"\x43\x01\x00\x80\x01\x00\x00\x00")
    result = verify_command_response(get_command_spec("7.4.5"), wrong_sub, _profile())
    assert result.result == VerificationResult.FAILED_NEEDS_ANALYSIS
    wrong_length = build_frame(0x30, b"\x80\x00")
    result = verify_command_response(get_command_spec("7.3.1"), wrong_length, _profile())
    assert result.result == VerificationResult.FAILED_NEEDS_ANALYSIS
