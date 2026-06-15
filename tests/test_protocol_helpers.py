import src.utr_inventory as inventory
import src.utr_protocol as protocol


def test_parse_little_endian_u16_reads_protocol_values():
    # テスト用の人工データ: 送信出力 24.0 dBm に相当する 240 を little-endian で表した値。
    assert protocol.parse_little_endian_u16(bytes([0xF0, 0x00])) == 240


def test_parse_little_endian_u16_rejects_invalid_length():
    # テスト用の人工データ: 2 バイト以外は受け付けない。
    import pytest

    with pytest.raises(ValueError):
        protocol.parse_little_endian_u16(bytes([0xF0]))


def test_calculate_sum_value_uses_low_byte_sum():
    # テスト用の人工データ: ROM_VERSION_CHECK の STX から ETX まで。
    frame_without_sum_cr = bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03])

    assert protocol.calculate_sum_value(frame_without_sum_cr) == 0xE5


def test_verify_sum_value_accepts_valid_frame_and_rejects_broken_sum():
    # テスト用の人工データ: ROM_VERSION_CHECK の完全フレーム。
    valid_frame = bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03, 0xE5, 0x0D])
    broken_sum_frame = bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03, 0xE4, 0x0D])

    assert protocol.verify_sum_value(valid_frame) is True
    assert protocol.verify_sum_value(broken_sum_frame) is False


def test_convert_rssi_handles_positive_and_negative_values():
    # テスト用の人工データ。現行実装に基づくテストであり、実機RSSI仕様は要仕様書確認。
    assert inventory.convert_rssi("0032") == 5.0
    # 0xFFCE は signed 16bit で -50、-50 / 10 = -5.0。
    assert inventory.convert_rssi("FFCE") == -5.0


def test_parse_nack_response_known_and_unknown_codes():
    # テスト用の人工データ: error code は parse_nack_response が参照する index 5 に置く。
    antenna_error = bytes([0x02, 0x00, 0x31, 0x02, 0x90, 0x68, 0x03, 0x00, 0x0D])
    sum_error = bytes([0x02, 0x00, 0x31, 0x02, 0x90, 0x42, 0x03, 0x00, 0x0D])
    unknown_error = bytes([0x02, 0x00, 0x31, 0x02, 0x90, 0x99, 0x03, 0x00, 0x0D])

    assert protocol.parse_nack_response(antenna_error).startswith("CMD_ANT_ERROR")
    assert protocol.parse_nack_response(sum_error).startswith("SUM_ERROR")
    assert protocol.parse_nack_response(unknown_error) == "Unknown NACK error (0x99)"


def test_parse_data_frame_returns_frame_and_next_index():
    # テスト用の人工データ: ROM_VERSION_CHECK の完全フレーム。
    valid_frame = bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03, 0xE5, 0x0D])

    parsed_frame, next_index = protocol.parse_data_frame(valid_frame, 0)

    assert parsed_frame == valid_frame
    assert next_index == len(valid_frame)


def test_parse_data_frame_returns_none_for_short_data():
    # テスト用の人工データ: フレームとして短すぎるデータ。
    short_data = bytes([0x02, 0x00, 0x4F])

    parsed_frame, next_index = protocol.parse_data_frame(short_data, 0)

    assert parsed_frame is None
    assert next_index == 0


def test_check_inventory_ack_response_reads_little_endian_count():
    # テスト用の人工ACK風データ。実機ログではありません。
    # index 6:8 にリトルエンディアンの読み取り枚数 0x0003 を置く。
    inventory_ack = bytes([0x02, 0x00, 0x30, 0x04, 0x10, 0x00, 0x03, 0x00, 0x03, 0x4C, 0x0D])

    assert inventory.check_inventory_ack_response(inventory_ack) == 3


def test_parse_inventory_ack_response_reads_count_and_channel():
    # テスト用の人工ACKデータ: count=3, channel=5 を含む。
    inventory_ack = bytes([0x02, 0x00, 0x30, 0x05, 0x10, 0x00, 0x03, 0x00, 0x05, 0x03, 0x50, 0x0D])

    assert inventory.parse_inventory_ack_response(inventory_ack) == (3, 5)


def test_parse_inventory_param_response_returns_japanese_display_values():
    # テスト用の人工データ。仕様書の応答例をそのまま固定値として使用する。
    response = bytes([
        0x02, 0x00, 0x30, 0x0B, 0x41, 0x00, 0x1F, 0xDC, 0x81, 0x02,
        0x00, 0x00, 0x00, 0x00, 0x02, 0x03, 0x01, 0x0D,
    ])

    parsed = inventory.parse_inventory_param_response(response)

    assert parsed["parameter_type_text"] == "コマンドモード用のパラメータ"
    assert parsed["select_command_enabled"] is True
    assert parsed["q_auto_enabled"] is True
    assert parsed["anti_collision_enabled"] is True
    assert parsed["q_start"] == 3
    assert parsed["inventory_target"] == "A"
    assert parsed["session"] == "S0"
    assert parsed["sel"] == "SL"
    assert parsed["trext"] == "Use pilot tone"
    assert parsed["m"] == "M4"
    assert parsed["dr"] == "64/3"
    assert parsed["q_min"] == 1
    assert parsed["q_max"] == 8
    assert parsed["mem_bank"] == "TID"
    assert parsed["tid_enabled"] is False
    assert parsed["read_start_word_address_hex"] == "00000000"
    assert parsed["read_word_count"] == 2


def test_format_inventory_param_response_returns_display_lines():
    response = bytes([
        0x02, 0x00, 0x30, 0x0B, 0x41, 0x00, 0x1F, 0xDC, 0x81, 0x02,
        0x00, 0x00, 0x00, 0x00, 0x02, 0x03, 0x01, 0x0D,
    ])

    parsed = inventory.parse_inventory_param_response(response)
    lines = inventory.format_inventory_param_response(parsed)

    assert "パラメータの種類: コマンドモード用のパラメータ" in lines
    assert "Selectコマンド: 使用する" in lines
    assert "Q値の開始値: 3" in lines
    assert "TRext(Pilot tone): Use pilot tone" in lines
    assert "読み取り開始アドレス(Hex): 00000000" in lines
    assert "読み取りWord数: 2" in lines


def test_handle_inventory_response_appends_pc_uii_and_rssi():
    # テスト用の人工Inventory応答データ。実機ログではありません。
    # handle_inventory_response はSUM検証を担当しないため、SUMは正しくなくてもよい前提です。
    pc_uii = bytes([0x30, 0x00, 0xE2, 0x00])
    data_frame = bytes([
        0x02, 0x00, 0x6C, 0x09, 0x09,
        0xFF, 0xCE, 0x00, len(pc_uii),
        *pc_uii,
        0x03, 0x00, 0x0D,
    ])
    pc_uii_list = []
    rssi_list = []

    inventory.handle_inventory_response(data_frame, pc_uii_list, rssi_list)

    assert pc_uii_list == [pc_uii]
    assert rssi_list == [-5.0]
