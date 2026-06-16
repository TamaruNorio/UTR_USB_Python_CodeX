import src.utr_protocol as protocol


def build_nack_frame(detail=0x10, code1=0x68, code2=0x00, code3=0x00, code4=0x00):
    frame_without_sum_cr = bytes([
        0x02,
        0x00,
        0x31,
        0x0A,
        detail,
        code1,
        code2,
        code3,
        code4,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x03,
    ])
    return frame_without_sum_cr + bytes([protocol.calculate_sum_value(frame_without_sum_cr)]) + bytes([0x0D])


def message_text(frame):
    return "\n".join(protocol.format_nack_message(frame))


def test_parse_nack_frame_reads_basic_fields():
    frame = build_nack_frame(detail=0x10, code1=0x68, code2=0x82, code3=0x02, code4=0x00)

    parsed = protocol.parse_nack_frame(frame)

    assert parsed["raw_hex"] == frame.hex().upper()
    assert parsed["detail_command"] == 0x10
    assert parsed["error_code_1"] == 0x68
    assert parsed["error_code_2"] == 0x82
    assert parsed["error_code_3"] == 0x02
    assert parsed["error_code_4"] == 0x00


def test_cmd_ant_error_message_includes_antenna_check_points():
    text = message_text(build_nack_frame(code1=0x68))

    assert "CMD_ANT_ERROR" in text
    assert "アンテナが接続されているか" in text
    assert "使用CHと実際の接続CH" in text


def test_sum_error_message_includes_sum_check_points():
    text = message_text(build_nack_frame(code1=0x42))

    assert "SUM_ERROR" in text
    assert "SUM計算" in text
    assert "送信データ欠落" in text


def test_format_error_message_includes_length_and_parameter_check_points():
    text = message_text(build_nack_frame(code1=0x44))

    assert "FORMAT_ERROR" in text
    assert "データ長" in text
    assert "パラメータ範囲" in text


def test_uhf_ic_error_message_includes_error_code_2():
    text = message_text(build_nack_frame(code1=0x0A, code2=0x82))

    assert "CMD_UHF_IC_ERROR" in text
    assert "エラーコード2: 0x82" in text


def test_error_code_2_access_password_error_is_displayed():
    text = message_text(build_nack_frame(code1=0x0A, code2=0x82))

    assert "Accessパスワードエラー" in text
    assert "Access Password設定" in text


def test_error_code_2_not_detected_is_displayed():
    text = message_text(build_nack_frame(code1=0x0A, code2=0x80))

    assert "検出されない" in text
    assert "タグ距離" in text
    assert "送信出力" in text


def test_uhf_encode_error_code_3_epc_uii_write_error_is_displayed():
    text = message_text(build_nack_frame(code1=0x0A, code2=0x20, code3=0x02))

    assert "エラーコード3: 0x02" in text
    assert "EPC(UII)領域への書き込み時にエラー" in text


def test_unknown_code_is_displayed_without_error():
    text = message_text(build_nack_frame(code1=0x99))

    assert "仕様書未定義または未対応コード" in text
    assert "Raw:" in text


def test_short_frame_returns_clear_parse_error():
    text = message_text(b"\x02\x00\x31")

    assert "解析エラー" in text
    assert "NACKフレームが短すぎます" in text
    assert "Raw: 020031" in text


def test_formatted_message_includes_raw_hex():
    frame = build_nack_frame(code1=0x68)

    assert f"Raw: {frame.hex().upper()}" in message_text(frame)
