
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UTR-S201 シリーズ（USBシリアル接続）サンプルプログラム（無保証） V1.1.5
Python 3.10+ / Windows 10+ で動作確認想定

【概要】
このプログラムは、タカヤ製UTR-S201シリーズRFIDリーダライタ（USBシリアル接続モデル）を
Pythonから操作するためのGUIを持たないコマンドラインサンプルです。

【注意事項】
- すべての条件分岐を網羅（確認）しているわけではありません。
- 作りこみには、当社の製品の基礎的な知識が必要です。
- 該当製品のプロトコル仕様書も理解する必要があります。
- 機器の設定には、別途RWManagerを使用し、実際の動作における通信ログなどを確認ください。
- タイムアウトや再送、パケット分割等は環境に合わせて調整してください。

【前提】
- 事前にpyserialのインストールが必要です。
- Raspberry Pi4 (Raspbian GNU/Linux 11 (bullseye)) および Windows 10+ で動作確認されています。

【更新履歴】
- Revised :  `communicate(command, timeout=1)` 関数変更
             受信データ内部のSTX,ETX,SUM,CRのチェックを実施
             タイムアウト or ACK/NACK受信 にて、ループを抜ける
- 集計結果をファイル保存（追加モード）
- `ser`をglobalからローカルへ変更、引数に設定。
- 詳細コマンド確認を追加(ROMバージョンチェックのみ)
- 変数（小文字）と定数（大文字）に変更
- 定数名を変更（CMD_LOCATION、DETAIL_LOCATION、OUTPUT_CH_FREQ_LIST）

【TODOリスト】
- ACK/NACKの判断をする別関数があっても良いかもしれません。
- 文字入力も別関数でチェック（処理）しても良いかもしれません。
- 送信出力の変更ができれば良いかもしれません。
- 連続インベントリモードへの対応（受信のみ。パケット途中からとか）
  現状の関数だとACK/NACK受信しないと戻らない（コマンドモードのみ対応）
- アンテナ選択、設定変更などをどうするか検討が必要です。
- OUTPUT_CH_FREQ_LISTを辞書型にするか検討が必要です。
- レスポンスデータの詳細コマンドまで確認するようにすべきです。
- 経過時間の取得方法の検討（差分がマイナスになり正しく時間計測できない場合の検討）

【参考情報】
R/W(リーダライタ)の各種動作設定については、Windows版 UTR-RWManagerを使用してください。
シリアル通信コマンドの詳細は、通信プロトコル仕様書を熟読のこと。
[https://www.product.takaya.co.jp/rfid/download/uhf.html/](https://www.product.takaya.co.jp/rfid/download/uhf.html/)

[コマンド、レスポンスの基本フォーマット]
- STX(02h) 1バイト #Start Text
- アドレス  1バイト (RWのIDなど、デフォルトは 00h)
- コマンド  1バイト
- データ長  1バイト
- データ部  0～255バイト
- ETX(03h) 1バイト  #End Text
- SUM      1バイト　STXからETXまで
- CR(0Dh)  1バイト  '/r' キャリッジリターン
"""

# 関連モジュールをインポート
import sys
import time
import datetime
import re
import json
from dataclasses import dataclass

import serial
from   serial.tools import list_ports

from   typing       import List, Optional, Tuple
try:
    from src.utr_inventory import format_inventory_param_response, parse_inventory_param_response
    from src.utr_protocol import format_nack_message, parse_output_power_dbm
    from src.utr_result_export import build_result_summary, save_results_to_csv, save_results_to_json
    from src.utr_serial_ports import format_port_info, find_port_by_user_input, is_quit_input
    from src.utr_commands import (
        BUZZER_SOUND_NACK,
        PARAMETER_KIND_COMMAND_MODE,
        PARAMETER_KIND_FLASH,
        build_buzzer_command,
        build_check_antenna_command,
        build_read_antenna_switching_setting_command,
        build_write_antenna_switching_setting_command,
    )
    from src.utr_antenna import (
        AntennaCheckTarget,
        AntennaModelProfile,
        AntennaSwitchingSetting,
        RomVersionInfo,
        allows_4ch_sequential_inventory,
        format_antenna_switching_setting,
        format_check_antenna_result,
        format_antenna_numbers,
        format_rom_version_info,
        identify_model_key_from_rom,
        get_model_profile,
        list_model_profiles,
        parse_antenna_switching_setting_response,
        parse_antenna_switching_setting_write_response,
        parse_check_antenna_response,
        parse_rom_version_response,
    )
except ModuleNotFoundError:
    from utr_inventory import format_inventory_param_response, parse_inventory_param_response
    from utr_protocol import format_nack_message, parse_output_power_dbm
    from utr_result_export import build_result_summary, save_results_to_csv, save_results_to_json
    from utr_serial_ports import format_port_info, find_port_by_user_input, is_quit_input
    from utr_commands import (
        BUZZER_SOUND_NACK,
        PARAMETER_KIND_COMMAND_MODE,
        PARAMETER_KIND_FLASH,
        build_buzzer_command,
        build_check_antenna_command,
        build_read_antenna_switching_setting_command,
        build_write_antenna_switching_setting_command,
    )
    from utr_antenna import (
        AntennaCheckTarget,
        AntennaModelProfile,
        AntennaSwitchingSetting,
        RomVersionInfo,
        allows_4ch_sequential_inventory,
        format_antenna_switching_setting,
        format_check_antenna_result,
        format_antenna_numbers,
        format_rom_version_info,
        identify_model_key_from_rom,
        get_model_profile,
        list_model_profiles,
        parse_antenna_switching_setting_response,
        parse_antenna_switching_setting_write_response,
        parse_check_antenna_response,
        parse_rom_version_response,
    )


# UTR用 シリアル送信コマンドの定義
# 各コマンドはバイト列として定義されており、そのまま送信可能
COMMANDS = {
    # ROMバージョンの読み取りコマンド: リーダライタのファームウェアバージョンを確認
    'ROM_VERSION_CHECK': bytes([0x02, 0x00, 0x4F, 0x01, 0x90, 0x03, 0xE5, 0x0D]),
    # コマンドモードへの切り替えコマンド: リーダライタをコマンド制御可能な状態に設定
    'COMMAND_MODE_SET': bytes([0x02, 0x00, 0x4E, 0x07, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x03, 0x6A, 0x0D]),
    # UHF_Inventoryコマンド: RFタグを読み取るためのインベントリ操作を開始
    'UHF_INVENTORY': bytes([0x02, 0x00, 0x55, 0x01, 0x10, 0x03, 0x6B, 0x0D]),
    # UHF_GetInventoryParam: RFタグ読み取り時のインベントリ処理に使用するパラメータの取得
    'UHF_GET_INVENTORY_PARAM':bytes([0x02,0x00,0x55,0x02,0x41,0x00,0x03,0x9D,0x0D]),
    # UHF_SetInventoryParamコマンド: インベントリパラメータの設定 (必要に応じて変更、別途関数あり)
    'UHF_SET_INVENTORY_PARAM': bytes([0x02,0x00,0x55,0x09,0x30,0x00,0x81,0x00,0x00,0x00,0x00,0x00,0x00,0x03,0x14,0x0D]),
    # UHF送信出力設定読み取りコマンド: リーダライタの送信出力レベルを読み取り
    'UHF_READ_OUTPUT_POWER': bytes([0x02,0x00,0x55,0x03,0x43,0x01,0x00,0x03,0xA1,0x0D]),
    # UHF送信周波数チャンネル読み取りコマンド: リーダライタの送信周波数チャンネルを読み取り
    'UHF_READ_FREQ_CH': bytes([0x02,0x00,0x55,0x03,0x43,0x02,0x00,0x03,0xA2,0x0D]),
    # UHFブザー制御コマンド:応答要求＋ピー音
    'UHF_BUZZER_pi': bytes([0x02,0x00,0x42,0x02,0x01,0x00,0x03,0x4A,0x0D]),
    # UHFブザー制御コマンド:応答要求＋ピッピッピ音
    'UHF_BUZZER_pipipi': bytes([0x02,0x00,0x42,0x02,0x01,0x01,0x03,0x4B,0x0D]),
    # UHF書き込みコマンド（一例、使ってません）: RFタグへのデータ書き込み (このサンプルでは未使用)
    'UHF_WRITE': bytes([0x02,0x00,0x55,0x08,0x16,0x01,0x00,0x00,0x00,0x02,0x04,0x56,0x03,0xD5,0x0D]),
}

# 定数の定義 (プロトコル仕様に準拠)
HEADER_LENGTH     = 4        # STX, アドレス, コマンド, データ長 (各1バイト) の合計長
FOOTER_LENGTH     = 3        # ETX, SUM, CR (各1バイト) の合計長
STX : bytes       = b'\x02'  # Start Text: フレーム開始を示すバイト
ADD : bytes       = b'\x00'  # アドレス: リーダライタIDなど (設定により変化することあり)
ETX : bytes       = b'\x03'  # End Text: データ部の終了を示すバイト
CR  : bytes       = b'\x0D'  # Carriage Return: フレームの終端を示すバイト
ACK : bytes       = b'\x30'  # ACK (Acknowledgment): 正常応答
NACK: bytes       = b'\x31'  # NACK (Negative Acknowledgment): エラー応答
INV : bytes       = b'\x6C'  # インベントリコマンド: RFタグ読み取りコマンド
BUZ : bytes       = b'\x42'  # ブザーコマンド: ブザー制御コマンド
CMD_LOCATION      = 2        # フレーム内のコマンドバイトの位置 (0-indexed)
DETAIL_LOCATION   = 4        # フレーム内の詳細コマンドバイトの位置 (0-indexed)
DETAIL_ROM: bytes = b'\x90'  # ROMバージョン読み取りの詳細コマンド
DETAIL_INV: bytes = b'\x10'  # インベントリの詳細コマンド

# 出力チャンネルと周波数のマッピングリスト (MHz)
OUTPUT_CH_FREQ_LIST = [916.0, 916.2, 916.4, 916.6, 916.8, 917.0, 917.2, 917.4, 917.6, 917.8, 918.0, 918.2, 918.4, 918.6, 918.8, 919.0, 919.2, 919.4, 919.6, 919.8, 920.0, 920.2, 920.4, 920.6, 920.8, 921.0, 921.2, 921.4, 921.6, 921.8, 922.0, 922.2, 922.4, 922.6, 922.8, 923.0, 923.2, 923.4]
DEFAULT_BAUD_RATE = 115200

#【シリアルデータ通信関数】
# データ送信後に、受信データ解析を実施
# 制御フロー参照: https://www.product.takaya.co.jp/dcms_media/other/TDR-OTH-PROGRAMMING-103.pdf
# タイムアウトもしくは、ACK, NACKを受信したらループを抜ける
# 受信データが多い(たくさんのタグ:30枚以上を読み取りする場合など)は、
# タイムアウト時間を多くする必要あり。もしくはタイムアウト処理の方法を変更する。
def communicate(ser: serial.Serial, command: bytes, timeout: float = 1.0) -> bytes:
    """
    コマンドをシリアルポートに送信し、応答を受信して解析する。
    受信データを1バイトずつ解析(STX, CR, ETX, SUM)しながら
    正常なレスポンスコマンドのみを連結して返す。
    ACK/NACKを受信するか、タイムアウトが発生したら処理を終了する。

    Args:
        ser (serial.Serial): シリアル通信オブジェクト。
        command (bytes): 送信するコマンドバイト列。
        timeout (float): 受信タイムアウト時間（秒）。デフォルトは1秒。

    Returns:
        bytes: 受信した完全な応答フレームのバイト列。
    """
    complete_response  = b'' # 解析後の正常レスポンスを格納するバッファ
    receive_buffer: List[int] = []      # 受信バイトを一時的に保持するリスト
    buffer_length = 0        # receive_bufferの現在の長さ
    data_length = 0          # フレーム内のデータ長

    if ser is not None:
        # コマンド送信 (上位 -> RW)
        ser.write(command)

    # タイム計測開始（現在の時刻を取得）
    start_time = time.time()

    # シリアル受信、データ解析処理
    while True:
        # タイムアウト処理
        if (time.time() - start_time) > timeout:
            print("タイムアウト: レスポンスが一定時間内に受信されませんでした。")
            return complete_response

        if ser is not None:
            # 受信バッファにデータがあれば、1バイトずつ読み取り
            # ser.read(1)はバイト列を返すため、リストに格納するためにintに変換
            chunk = ser.read(1)
            if chunk:
                receive_buffer.append(chunk[0])
                buffer_length = len(receive_buffer) # バッファーの長さを取得

        # receive_buffer内になにかデータがあり、先頭がSTX(0x02)だったら、
        if receive_buffer:
            if receive_buffer[0] == STX[0]:
                # バッファ長がヘッダー長(4バイト)以上であれば、
                if buffer_length >= HEADER_LENGTH:
                    # データ長(4バイト目)を data_lengthに入力
                    data_length = receive_buffer[HEADER_LENGTH - 1]

                    # バッファ長が (データ長+ヘッダ長+フッタ長)以上であれば、
                    if buffer_length >= (data_length + HEADER_LENGTH + FOOTER_LENGTH):
                        # 最後位がCR(0x0D)であれば、
                        if receive_buffer[(data_length + HEADER_LENGTH + FOOTER_LENGTH) - 1] == CR[0]:
                            # ETXの位置にETX(0x03)があれば、
                            if receive_buffer[data_length + HEADER_LENGTH] == ETX[0]:
                                # SUM値の確認がTrueであれば、
                                # バイト列に変換してverify_sum_valueに渡す
                                current_frame_bytes = bytes(receive_buffer[:(data_length + HEADER_LENGTH + FOOTER_LENGTH)])
                                if verify_sum_value(current_frame_bytes):
                                    # 戻り値に、フォーマット確認済みのバッファを追加
                                    complete_response += current_frame_bytes

                                    # ACK, NACK受信していたら抜ける
                                    if receive_buffer[CMD_LOCATION] in [ACK[0], NACK[0]]:
                                        receive_buffer = [] # バッファをクリア
                                        return complete_response

                                    # 確認済みバッファをクリアし、次のフレームの解析へ
                                    receive_buffer = receive_buffer[(data_length + HEADER_LENGTH + FOOTER_LENGTH):]

                                else:
                                    # SUMが違ったので先頭バイトを削除し、再同期を試みる
                                    receive_buffer = receive_buffer[1:]

                            else:
                                # ETXが違ったので先頭バイトを削除し、再同期を試みる
                                receive_buffer = receive_buffer[1:]

                        else:
                            # CRが違ったので先頭バイトを削除し、再同期を試みる
                            receive_buffer = receive_buffer[1:]

                    else:
                        # バッファ長が (データ長+ヘッダ長+フッタ長)未満なら、まだフレームが完全でないので継続
                        continue

                else:
                    # バッファ長がヘッダー長(4バイト)未満なら、まだヘッダーが完全でないので継続
                    continue

            else:
                # STXがデータの先頭に無かったので先頭バイトを削除し、STXを探索
                receive_buffer = receive_buffer[1:]


# インベントリのレスポンスデータ(コマンドが0x6C)から、PC_UIIデータと、RSSI値を切り出す
def handle_inventory_response(data_frame: bytes, pc_uii_list: List[bytes], rssi_list: List[float]) -> None:
    """
    インベントリのレスポンス1フレームからPC+UIIデータとRSSI値を抽出し、リストに格納する。

    Args:
        data_frame (bytes): 受信したデータフレーム（STXからCRまで）。
        pc_uii_list (List[bytes]): 抽出したPC+UIIデータを格納するリスト。
        rssi_list (List[float]): 抽出したRSSI値を格納するリスト。
    """
    # [インベントリ ACKレスポンス フォーマット]
    #  STX      0x02
    #  アドレス  0x00 #固定では無い
    #  コマンド  0x6C
    #  データ長  5 + n
    #  データ部  0x09   1バイト 詳細コマンド
    #           RSSI   2バイト
    #           RSSI
    #           ANGLE  1バイト
    #           n      1バイト　PC+UIIのバイト数
    #           PC+UII nバイト
    #  ETX      0x03
    #  SUM      SUM
    #  CR       0x0D

    # 9バイト目の 'n' をPC+UIIのバイト数に入力
    pc_uii_length = data_frame[8]
    # pc_uii_lengthの長さだけデータをスライス（切り出し）します
    pc_uii_data = data_frame[9:9 + pc_uii_length]

    # 切り出したデータをリストへ追加
    pc_uii_list.append(pc_uii_data)

    # RSSI値の計算 (フレームの5バイト目と6バイト目を使用)
    rssi_value = convert_rssi(data_frame[5:7].hex())
    # RSSI値をリストへ追加
    rssi_list.append(rssi_value)


# インベントリ時のACKのレスポンスデータから読み取り枚数を取得する。
def check_inventory_ack_response(data_frame: bytes) -> Tuple[int, int]:
    """
    インベントリ時のACK応答フレームから、期待される読み取り枚数を抽出して返す。

    Args:
        data_frame (bytes): 受信したACK応答フレーム。

    Returns:
        Tuple[int, int]: 期待される読み取り枚数とチャンネル番号。
    """
    # 7バイト目と8バイト目（Pythonのインデックスでは6:8）が読み取り枚数
    # リトルエンディアンの順序で整数に変換
    read_count = int.from_bytes(data_frame[6:8], byteorder='little')
    channel = data_frame[8]
    return read_count, channel


# データフレームを解析し、STX-ETX-SUM-CRまでを抜き出す
def parse_data_frame(data: bytes, index: int) -> Tuple[Optional[bytes], int]:
    """
    受信したデータバイト列から、STXからCRまでの完全な1フレームを抽出する。

    Args:
        data (bytes): 受信したデータバイト列。
        index (int): 現在の解析開始位置。

    Returns:
        Tuple[Optional[bytes], int]: 
            - 抽出されたフレーム (bytes)。完全なフレームが見つからない場合はNone。
            - 次の解析開始位置 (int)。
    """
    # フレームの最小長をチェック (ヘッダー長 + フッター長)
    if len(data) >= (index + HEADER_LENGTH + FOOTER_LENGTH):
        # 4バイト目のデータ長を確認し、フレーム全体の長さを算出
        data_length_in_frame = data[index + 3] # フレーム内のデータ長フィールド
        total_frame_len = data_length_in_frame + HEADER_LENGTH + FOOTER_LENGTH

        # フレーム全体がバッファに存在するかを確認
        if len(data) >= (index + total_frame_len):
            # データの最後がCR(0x0D)であれば
            if data[(index + total_frame_len) - 1] == CR[0]:
                # 解析したデータフレームと次の開始位置を戻す
                return data[index:(index + total_frame_len)], (index + total_frame_len)

    # データが短かったり、完全なフレームが見つからない場合は、元の開始位置のみを返す
    return None, index


# シリアル受信したデータ(受信解析後)の中からタグの情報などを抜き出す
# インベントリコマンド用
def received_data_parse(data: bytes) -> Tuple[List[bytes], List[float], Optional[int], Optional[int]]:
    """
    受信したバイト列から複数のフレームを走査し、インベントリ結果を解析する。
    PC+UIIリスト、RSSIリスト、期待される読み取り枚数を抽出する。

    Args:
        data (bytes): 受信した生のデータバイト列。

    Returns:
        Tuple[List[bytes], List[float], Optional[int], Optional[int]]:
            - pc_uii_list (List[bytes]): 読み取られたPC+UIIデータのリスト。
            - rssi_list (List[float]): 読み取られたRSSI値のリスト。
            - expected_read_count (Optional[int]): 期待される読み取りタグ数 (ACKフレームから取得)。
            - read_channel (Optional[int]): 読み取り時のチャンネル番号 (ACKフレームから取得)。
    """
    pc_uii_list: List[bytes] = []  # UII格納用
    rssi_list: List[float] = []  # RSSI値格納用
    expected_read_count: Optional[int] = None   # ACKレスポンスから取得した読み取り枚数
    read_channel: Optional[int] = None   # ACKレスポンスから取得した読み取りチャンネル番号

    i = 0
    while i < len(data):
        if data[i] == STX[0]:   # STX: 0x02 があればフレームの開始とみなす
            # データ解析
            data_frame, next_idx = parse_data_frame(data, i)

            if data_frame:
                if verify_sum_value(data_frame): # チェックサムを検証
                    # フレームの3バイト目(CMD_LOCATION)をcommandにいれる
                    command = bytes([data_frame[CMD_LOCATION]])
                    # 詳細コマンドを抽出 (存在する場合)
                    detail_command = bytes([data_frame[DETAIL_LOCATION]]) if len(data_frame) > DETAIL_LOCATION else b''

                    if command == INV:
                        # コマンドが0x6C (INV) なら、インベントリの応答として処理
                        handle_inventory_response(data_frame, pc_uii_list, rssi_list)

                    elif command == ACK:
                        # コマンドがACK (0x30) なら、ACKの応答として処理
                        if detail_command == DETAIL_INV:
                            # 詳細コマンドがインベントリACK (0x10) なら、読み取り枚数を取得
                            expected_read_count, read_channel = check_inventory_ack_response(data_frame)
                        # else: 他のACK応答はここでは特に処理しない

                    elif command == NACK:
                        # コマンドがNACK (0x31) なら、NACKの応答として処理
                        print_nack_message(data_frame) # NACKエラーメッセージを表示

                else:
                    print("サム値が正しくありません（途中までの結果を返します）")
                    # この処理以前に解析したデータ(タグIDなど）を返す
                    return pc_uii_list, rssi_list, expected_read_count, read_channel

                # 次の開始位置に変更
                i = next_idx

            else:
                # 完全なフレームが見つからなかった場合、現在の解析を打ち切る
                print("データがありません、または不完全なフレームです")
                # この処理以前に解析したデータ(タグIDなど）を返す
                return pc_uii_list, rssi_list, expected_read_count, read_channel
        else:
            # STXが見つからない場合は1バイト進める
            i += 1

    # 期待される読み取り枚数と実際に読み取った枚数が一致しない場合の警告
    if expected_read_count is not None:
        if expected_read_count != len(pc_uii_list):
            # 以下、(受信経路や上位のノイズなどで)受信データの不整合が
            # 発生したときに表示されます。(デバッグコードではありません)
            print("タグの読み取り数とpc_uii_listの個数が一致しません")
            print("タグの読み取り予定数: ", expected_read_count)
            print("pc_uii_listの個数   : ",  len(pc_uii_list))

    # 解析したデータ(タグIDなど）を返す
    return pc_uii_list, rssi_list, expected_read_count, read_channel


# NACK応答時のエラー解析(初歩、一例) 全部は網羅してません。
def print_nack_message(nack_response: bytes) -> None:
    """NACK応答を現場確認向けの複数行で表示する。"""
    for line in format_nack_message(nack_response):
        print(line)


def parse_baud_rate_input(value: str) -> int:
    """ボーレート入力を整数に変換する。未入力はデフォルト値を使う。"""
    normalized = value.strip()
    if normalized == "":
        return DEFAULT_BAUD_RATE
    return int(normalized)


# SUM値計算
def calculate_sum_value(data: bytes) -> int:
    """
    バイト列の合計値（チェックサム）を計算する。
    STXからETXまでのバイトの合計の下位1バイトを返す。

    Args:
        data (bytes): チェックサムを計算するデータのバイト列 (STX-ETXまで)。

    Returns:
        int: 計算されたチェックサム（下位1バイト）。
    """
    sum_value = 0
    for byte in data:
        sum_value += byte
    sum_value &= 0xFF  # 下位1バイトに制限 (256で割った余り)
    return sum_value


# サム値を検証する。
def verify_sum_value(data_frame: bytes) -> bool:
    """
    データフレーム内のチェックサムが正しいか検証する。
    STXからETXまでの合計値と、データ内にあるSUM値が一致するかを確認する。

    Args:
        data_frame (bytes): 検証するデータフレーム（STXからCRまで）。

    Returns:
        bool: チェックサムが正しい場合はTrue、そうでない場合はFalse。
    """
    data_length = len(data_frame)

    # フレームの最後から2番目のバイトが期待されるSUM値
    expect_sum_value = data_frame[data_length - 2]

    # STXからETXまでのバイトの合計を計算
    calculated_sum_value = calculate_sum_value(data_frame[:data_length - 2])

    return expect_sum_value == calculated_sum_value


# RSSI値計算
def convert_rssi(rssi_hex_value: str) -> float:
    """
    RSSI値(無線信号強度の指標)を計算する。
    レスポンスの6〜7バイト目を符号付き16ビットとして扱い、
    10進数に変換してから10で割る。
    ※詳しくは、プロトコル仕様書を参照

    Args:
        rssi_hex_value (str): RSSIの16進数文字列（例: "FFC0"）。

    Returns:
        float: 変換されたRSSI値（dBm）。
    """
    # 16進数文字列を整数に変換
    rssi_int = int(rssi_hex_value, 16)

    # 16ビット符号付き整数として扱う
    if rssi_int & 0x8000:  # 最上位ビットが1の場合（負の数）
        rssi_int = -(0x10000 - rssi_int)

    # 10で割ってdBm値に変換
    return rssi_int / 10.0


# 集計ログ保存
def save_results_to_file(filename: str, total_iterations: int, total_read_time: float,
                         total_read_count: int, pc_uii_count_dict: dict) -> None:
    """
    インベントリの結果を集計し、指定されたファイルに追記する。

    Args:
        filename (str): 結果を保存するファイル名。
        total_iterations (int): 総繰り返し回数。
        total_read_time (float): 総読み取り時間（秒）。
        total_read_count (int): 総読み取りタグ数。
        pc_uii_count_dict (dict): PC+UIIごとの読み取り回数を格納した辞書。
    """
    with open(filename, 'a', encoding="utf-8") as f:
        current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write("\n# -*- coding: utf-8 -*-\n") # ファイルエンコーディング指定
        f.write(f"\n=== 集計結果 ({current_datetime}) ===\n")
        f.write(f"総繰り返し回数: {total_iterations}\n")
        f.write(f"総読み取り時間: {total_read_time:.2f} 秒\n")
        if total_iterations > 0:
            f.write(f"平均読み取り枚数: {total_read_count / total_iterations:.2f} 枚\n")
        f.write("各PC+UIIデータの読み取り回数:\n")
        for pc_uii_hex, count in pc_uii_count_dict.items():
            f.write(f"{pc_uii_hex}: {count} 回\n")
        f.write("========= ここまで ============\n\n\n")


def print_available_ports(ports) -> None:
    """Print available serial ports with details useful for field support."""
    print("利用可能なCOMポート:")
    for i, port in enumerate(ports):
        for line in format_port_info(port, i):
            print(f"  {line}")


def prompt_for_port_name(ports) -> str:
    """Prompt until the user selects a serial port or quits."""
    print_available_ports(ports)

    if len(ports) == 1:
        while True:
            answer = input("COMポートが1件だけ見つかりました。このポートを使用しますか？（Enter/y=使用、n=選択、q=終了）: ").strip()
            if answer == "" or answer.lower() == "y":
                return ports[0].device
            if answer.lower() == "n":
                break
            if is_quit_input(answer):
                print("COMポート選択を終了します。")
                sys.exit(0)
            print("無効な入力です。Enter、y、n、q のいずれかを入力してください。")

    while True:
        user_input = input("接続するCOMポートの番号またはCOM名を入力してください（終了は'q'）: ")
        if is_quit_input(user_input):
            print("COMポート選択を終了します。")
            sys.exit(0)

        selected_port = find_port_by_user_input(user_input, ports)
        if selected_port is not None:
            return selected_port.device

        print("無効な入力です。表示された番号または COM名（例: COM6）を入力してください。")


def parse_yes_no_answer(value: str, default: bool = False) -> Optional[bool]:
    """Parse a y/n answer. Returns None when the input is invalid."""
    normalized = value.strip().lower()
    if normalized == "":
        return default
    if normalized == "y":
        return True
    if normalized == "n":
        return False
    return None


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ask a y/n question until a valid answer is entered."""
    while True:
        answer = parse_yes_no_answer(input(prompt), default=default)
        if answer is not None:
            return answer
        print("無効な入力です。y または n を入力してください。")


@dataclass(frozen=True)
class InventoryAntennaSelection:
    """Inventoryで使用するアンテナ選択結果。

    restore_setting:
        プログラム終了時に復元する、変更前のコマンドモード用アンテナ設定。

    selected_targets:
        Inventoryで順番に使用するアンテナ一覧。
        例: [ANT0, ANT1] の場合、ANT0でInventoryしてからANT1でInventoryします。
    """

    restore_setting: AntennaSwitchingSetting
    selected_targets: list[AntennaCheckTarget]


def prompt_for_antenna_model_profile(identified_model_key: str | None = None) -> AntennaModelProfile:
    """アンテナ接続チェック対象の機種を選択します。

    Args:
        identified_model_key:
            ROMシリーズ名コードと仕様書上の機種対応表を照合して確定した機種キー。
            一致する場合はEnterで採用できます。
    """
    profiles = list_model_profiles()
    identified_index: int | None = None

    print("アンテナ接続チェック対象の機種を選択してください。")
    for index, profile in enumerate(profiles, start=1):
        marker = ""
        if identified_model_key == profile.key:
            marker = "  ← ROMバージョンから仕様書上確定"
            identified_index = index
        print(f"[{index}] {profile.display_name}{marker}")
        print(f"    {profile.note}")

    while True:
        prompt = "機種番号を入力してください（終了は'q'）: "
        if identified_index is not None:
            prompt = f"機種番号を入力してください（Enter=仕様書照合機種[{identified_index}]、終了は'q'）: "

        value = input(prompt).strip()
        if value == "" and identified_index is not None:
            return profiles[identified_index - 1]
        if is_quit_input(value):
            print("アンテナ接続チェックを中止します。")
            raise KeyboardInterrupt

        try:
            selected_index = int(value)
        except ValueError:
            print("入力エラー: 表示された番号を入力してください。")
            continue

        if 1 <= selected_index <= len(profiles):
            return profiles[selected_index - 1]

        print("入力エラー: 表示された番号の範囲で入力してください。")


def read_and_print_antenna_switching_setting(
    ser: serial.Serial,
    parameter_kind: int,
) -> Optional[AntennaSwitchingSetting]:
    """アンテナ切替設定を読み取り、画面へ表示します。

    Returns:
        AntennaSwitchingSetting | None:
            正常に読み取れた場合は解析結果。
            通信エラーやNACKの場合は None。

    注意:
        読み取り専用です。FLASHやRAMへの書き込みは行いません。
    """
    response = communicate(
        ser,
        build_read_antenna_switching_setting_command(parameter_kind=parameter_kind),
    )

    if re.match(STX + b'.' + ACK, response):
        try:
            setting = parse_antenna_switching_setting_response(response)
        except ValueError as exc:
            print(f"アンテナ切替設定レスポンスの解析に失敗しました: {exc}")
            print("Raw:", response.hex().upper())
            return None

        for line in format_antenna_switching_setting(setting):
            print(line)
        return setting
    elif re.match(STX + b'.' + NACK, response):
        print_nack_message(response)
        return None
    else:
        print("アンテナ切替設定の読み取りで ACK/NACK がありません。")
        print("Raw:", response.hex().upper())
        return None


def check_and_print_antennas(ser: serial.Serial, profile: AntennaModelProfile) -> list[AntennaCheckTarget]:
    """UHF_CheckAntennaで、機種に応じたアンテナ接続確認を行います。

    Args:
        ser (serial.Serial): 接続済みのシリアル通信オブジェクト。
        profile (AntennaModelProfile): 機種別アンテナプロファイル。

    Returns:
        list[AntennaCheckTarget]:
            接続OKだったアンテナ対象のリスト。

    注意:
        この処理は接続確認コマンドだけを送信します。
        アンテナ切替設定やFLASH設定は変更しません。
    """
    print("アンテナ接続チェックを開始します。")
    print(f"対象機種: {profile.display_name}")

    connected_targets: list[AntennaCheckTarget] = []

    for target in profile.check_targets:
        print(f"{target.label} 接続確認中... {target.description}")
        response = communicate(ser, build_check_antenna_command(target.number))

        if re.match(STX + b'.' + ACK, response):
            try:
                result = parse_check_antenna_response(response)
            except ValueError as exc:
                print(f"  解析エラー: {exc}")
                print("  Raw:", response.hex().upper())
                continue

            print(" ", format_check_antenna_result(result, profile=profile))
            if result.is_connected:
                connected_targets.append(target)
        elif re.match(STX + b'.' + NACK, response):
            print_nack_message(response)
        else:
            print("  ACK/NACK がありません。")
            print("  Raw:", response.hex().upper())

    connected_text = ", ".join(target.label for target in connected_targets) if connected_targets else "なし"
    print("アンテナ接続チェック結果:")
    print(f"  接続OK: {connected_text}")
    print("補足: この時点ではアンテナ設定を書き換えていません。")
    return connected_targets


def filter_inventory_antenna_targets(
    connected_targets: list[AntennaCheckTarget],
    flash_setting: AntennaSwitchingSetting,
) -> list[AntennaCheckTarget]:
    """Inventory対象にできるアンテナだけを抽出します。

    条件:
        1. UHF_CheckAntennaで接続OK
        2. FLASHデータで使用許可あり

    補足:
        物理的に接続OKでも、FLASH側で使用許可がないアンテナは
        コマンドモード用パラメータへ書き込むとNACKになる可能性があります。
    """
    flash_enabled_numbers = set(flash_setting.enabled_antennas)
    available_targets: list[AntennaCheckTarget] = []

    for target in connected_targets:
        if target.number in flash_enabled_numbers:
            available_targets.append(target)
        else:
            print(
                f"{target.label} は接続OKですが、FLASHデータで使用許可がないためInventory候補から外します。"
            )

    return available_targets


def parse_inventory_antenna_selection_input(
    available_targets: list[AntennaCheckTarget],
    value: str,
) -> Optional[list[AntennaCheckTarget]]:
    """Inventory対象アンテナの入力文字列を解析します。

    対応入力:
        q      : 選択中止
        0      : ANT0だけ選択
        1      : ANT1だけ選択
        0,1    : ANT0、ANT1を順番に選択
        all    : 候補アンテナをすべて選択

    Returns:
        list[AntennaCheckTarget] | None:
            選択されたアンテナ一覧。
            q の場合は None。

    Raises:
        ValueError:
            候補にないアンテナ番号や不正な入力の場合。
    """
    normalized = value.strip().lower()
    if is_quit_input(normalized):
        return None

    if normalized == "all":
        return list(available_targets)

    if normalized == "":
        raise ValueError("空入力です。例: 0 / 1 / 0,1 / all")

    target_by_number = {target.number: target for target in available_targets}
    selected_targets: list[AntennaCheckTarget] = []
    selected_numbers: set[int] = set()

    for part in normalized.split(","):
        part = part.strip()
        if part == "":
            raise ValueError("カンマの前後にアンテナ番号を入力してください。")

        try:
            selected_number = int(part)
        except ValueError as exc:
            raise ValueError("アンテナ番号は数値、または all で入力してください。") from exc

        if selected_number not in target_by_number:
            raise ValueError("候補に表示されているアンテナ番号を入力してください。")

        # 同じ番号を重複入力した場合は1回だけ使います。
        if selected_number not in selected_numbers:
            selected_targets.append(target_by_number[selected_number])
            selected_numbers.add(selected_number)

    if not selected_targets:
        raise ValueError("Inventoryに使用するアンテナが選択されていません。")

    return selected_targets


INVENTORY_ANTENNA_SELECTION_PROMPT = (
    "Inventoryに使用するアンテナ番号を入力してください（例: 0,1 / all）。\n"
    "アンテナを指定しない場合は q を入力してください。\n"
    "q を入力するとアンテナ設定を変更せず、現在のコマンドモード用アンテナ設定でInventoryを続行します。\n"
    "入力: "
)


def prompt_for_inventory_antenna_targets(
    available_targets: list[AntennaCheckTarget],
) -> list[AntennaCheckTarget]:
    """Inventoryで使用するアンテナをユーザーに選択してもらいます。

    複数選択した場合は、同時指定ではなく順次切替でInventoryします。
    例: 0,1 → ANT0でInventory → ANT1でInventory
    """
    if not available_targets:
        print("Inventoryに使用できるアンテナがありません。アンテナ設定は変更しません。")
        return []

    print("")
    print("Inventoryに使用できるアンテナ候補:")
    for target in available_targets:
        print(f"[{target.number}] {target.label}（{target.description}）")

    if len(available_targets) == 1:
        target = available_targets[0]
        if ask_yes_no(
            f"接続OKのアンテナが1つだけのため、{target.label}をInventoryに使用しますか？ [Y/n]: ",
            default=True,
        ):
            return [target]
        print("アンテナ設定は変更しません。")
        return []

    print("複数選択できます。例: 0 / 1 / 0,1 / all")
    print("複数選択時は、同時使用ではなく順番にアンテナを切り替えてInventoryします。")

    while True:
        value = input(INVENTORY_ANTENNA_SELECTION_PROMPT).strip()

        try:
            selected_targets = parse_inventory_antenna_selection_input(available_targets, value)
        except ValueError as exc:
            print(f"入力エラー: {exc}")
            continue

        if selected_targets is None:
            print("アンテナ設定は変更しません。")
            return []

        selected_text = ", ".join(target.label for target in selected_targets)
        print(f"Inventory対象アンテナ: {selected_text}")
        return selected_targets


def write_command_mode_antenna_setting(
    ser: serial.Serial,
    current_setting: AntennaSwitchingSetting,
    target: AntennaCheckTarget,
) -> Optional[AntennaSwitchingSetting]:
    """コマンドモード用アンテナ設定を一時変更します。

    Args:
        ser: 接続済みシリアルオブジェクト。
        current_setting: 現在のコマンドモード用アンテナ切替設定。
            順次切替では、直前に書き込んだアンテナ設定を渡します。
        target: Inventoryで使用したいアンテナ。

    Returns:
        AntennaSwitchingSetting | None:
            切替不要または書き込み成功の場合は、現在有効なアンテナ設定。
            書き込み失敗の場合は None。

    注意:
        FLASHには書き込みません。コマンドモード用パラメータだけを一時変更します。
    """
    selected_mask = 1 << target.number

    if current_setting.antenna_mask == selected_mask:
        print(f"コマンドモード用アンテナ設定はすでに {target.label} です。そのままInventoryに使用します。")
        return current_setting

    print("")
    print("コマンドモード用アンテナ設定を一時変更します。")
    print(f"変更前: {format_antenna_numbers(current_setting.enabled_antennas)}")
    print(f"変更後: {target.label}（{target.description}）")
    print("FLASHは変更しません。")

    response = communicate(
        ser,
        build_write_antenna_switching_setting_command(
            parameter_kind=PARAMETER_KIND_COMMAND_MODE,
            switching_mode=current_setting.switching_mode,
            antenna_id_output_enabled=current_setting.antenna_id_output_enabled,
            antenna_mask=selected_mask,
        ),
    )

    if re.match(STX + b'.' + ACK, response):
        try:
            written_setting = parse_antenna_switching_setting_write_response(response)
        except ValueError as exc:
            print(f"アンテナ切替設定書き込みレスポンスの解析に失敗しました: {exc}")
            print("Raw:", response.hex().upper())
            return None

        print("コマンドモード用アンテナ設定を一時変更しました。")
        for line in format_antenna_switching_setting(written_setting):
            print(line)
        return written_setting

    if re.match(STX + b'.' + NACK, response):
        print_nack_message(response)
        return None

    print("アンテナ切替設定の書き込みで ACK/NACK がありません。")
    print("Raw:", response.hex().upper())
    return None


def restore_command_mode_antenna_setting(
    ser: serial.Serial,
    original_setting: AntennaSwitchingSetting,
) -> bool:
    """コマンドモード用アンテナ設定を元に戻します。"""
    print("")
    print("コマンドモード用アンテナ設定を元に戻します。")
    print(f"復元対象: {format_antenna_numbers(original_setting.enabled_antennas)}")
    print("FLASHは変更していません。")

    response = communicate(
        ser,
        build_write_antenna_switching_setting_command(
            parameter_kind=PARAMETER_KIND_COMMAND_MODE,
            switching_mode=original_setting.switching_mode,
            antenna_id_output_enabled=original_setting.antenna_id_output_enabled,
            antenna_mask=original_setting.antenna_mask,
        ),
    )

    if re.match(STX + b'.' + ACK, response):
        print("コマンドモード用アンテナ設定を元に戻しました。")
        return True
    elif re.match(STX + b'.' + NACK, response):
        print("コマンドモード用アンテナ設定の復元でNACKを受信しました。")
        print_nack_message(response)
        return False
    else:
        print("コマンドモード用アンテナ設定の復元で ACK/NACK がありません。")
        print("Raw:", response.hex().upper())
        return False


def drain_serial_input_until_quiet(
    ser: serial.Serial,
    quiet_seconds: float = 0.8,
    max_seconds: float = 5.0,
) -> int:
    """Discard delayed serial input until the input buffer stays quiet."""
    read = getattr(ser, "read", None)
    if not callable(read):
        return 0

    deadline = time.monotonic() + max_seconds
    quiet_deadline = time.monotonic() + quiet_seconds
    drained_total = 0

    while time.monotonic() < deadline:
        waiting = int(getattr(ser, "in_waiting", 0) or 0)

        if waiting > 0:
            drained = read(waiting)
            drained_total += len(drained)
            quiet_deadline = time.monotonic() + quiet_seconds
            continue

        if time.monotonic() >= quiet_deadline:
            break

        time.sleep(0.05)

    return drained_total


def clear_serial_input_buffer_before_restore(ser: serial.Serial) -> None:
    """復元コマンド送信前に、遅延して残った受信データを可能な限り読み捨てます。"""
    reset_input_buffer = getattr(ser, "reset_input_buffer", None)
    if not callable(reset_input_buffer):
        return

    try:
        reset_input_buffer()
        drained_total = drain_serial_input_until_quiet(ser)
        print("復元前に受信バッファをクリアしました。")
        if drained_total:
            print(f"復元前の残データを読み捨てました: {drained_total} bytes")
    except Exception:
        print("復元前の受信バッファクリアに失敗しました。復元処理は継続します。")


def restore_antenna_setting_safely(
    ser: serial.Serial,
    antenna_selection: Optional[InventoryAntennaSelection],
) -> None:
    """中断時でも可能な限りコマンドモード用アンテナ設定を復元します。"""
    if antenna_selection is None:
        return

    clear_serial_input_buffer_before_restore(ser)

    try:
        restored = restore_command_mode_antenna_setting(ser, antenna_selection.restore_setting)
    except Exception as exc:
        print("コマンドモード用アンテナ設定の復元に失敗しました。")
        print("機器側の現在設定をUTRRWManagerまたは再実行時の読み取りで確認してください。")
        print(f"復元エラー: {exc}")
        return

    if not restored:
        print("コマンドモード用アンテナ設定の復元に失敗しました。")
        print("機器側の現在設定をUTRRWManagerまたは再実行時の読み取りで確認してください。")


def save_inventory_results(
    total_iterations: int,
    total_read_time: float,
    total_read_count: int,
    pc_uii_count_dict: dict,
    inventory_result_items: list[dict],
) -> None:
    """Inventory集計結果をTXT/CSV/JSONへ保存します。"""
    if not should_save_inventory_results(total_iterations):
        print("Inventoryが実行されていないため、集計結果は保存しません。")
        return

    try:
        save_results_to_file(
            "inventory_results.txt",
            total_iterations,
            total_read_time,
            total_read_count,
            pc_uii_count_dict,
        )
        print("集計結果を inventory_results.txt に保存しました。")
    except OSError as e:
        print(f"TXT保存エラー: {e}")

    summary = build_result_summary(
        total_iterations,
        total_read_time,
        total_read_count,
        pc_uii_count_dict,
        items=inventory_result_items,
    )
    try:
        save_results_to_csv("inventory_results.csv", summary)
        print("集計結果を inventory_results.csv に保存しました。")
    except OSError as e:
        print(f"CSV保存エラー: {e}")
    try:
        save_results_to_json("inventory_results.json", summary)
        print("集計結果を inventory_results.json に保存しました。")
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"JSON保存エラー: {e}")


def should_save_inventory_results(total_iterations: int) -> bool:
    """Inventoryを1回以上実行した場合だけ集計結果を保存します。"""
    return total_iterations > 0


def format_pc_uii_for_display(pc_uii_hex: str, mask: bool = False) -> str:
    """PC+UIIの画面表示用文字列を返します。

    Args:
        pc_uii_hex: PC+UIIを16進文字列にした値。
        mask: Trueの場合、実タグIDを画面へ出さず「省略」と表示します。

    Returns:
        str: 画面表示に使うPC+UII文字列。

    注意:
        この関数は画面表示だけを制御します。集計キーや保存データは変更しません。
        タグ別の読み取り回数を壊さないためです。
    """
    if mask:
        return "省略"
    return pc_uii_hex


def close_serial_safely(ser: serial.Serial) -> None:
    """シリアル接続を可能な限り閉じます。"""
    try:
        if ser and ser.is_open:
            ser.close()
        print("接続を閉じました。")
    except Exception as exc:
        print(f"シリアルポートのクローズに失敗しました: {exc}")


def finish_inventory_session(
    ser: serial.Serial,
    antenna_selection: Optional[InventoryAntennaSelection],
    total_iterations: int,
    total_read_time: float,
    total_read_count: int,
    pc_uii_count_dict: dict,
    inventory_result_item_dict: dict,
) -> None:
    """Inventory終了時の復元、保存、切断をまとめて実行します。"""
    restore_antenna_setting_safely(ser, antenna_selection)
    save_inventory_results(
        total_iterations,
        total_read_time,
        total_read_count,
        pc_uii_count_dict,
        list(inventory_result_item_dict.values()),
    )
    close_serial_safely(ser)


def run_optional_antenna_check(
    ser: serial.Serial,
    rom_info: RomVersionInfo | None = None,
) -> Optional[InventoryAntennaSelection]:
    """必要に応じて、アンテナ設定表示と接続確認を行います。

    Returns:
        InventoryAntennaSelection | None:
            Inventoryで使用するアンテナが選択された場合は、
            復元用の変更前設定と選択アンテナ一覧を返します。
            変更しない場合は None。

    ROMシリーズ名コードから仕様書上の機種が確定できる場合は、
    機種番号を手入力させず、その機種プロファイルを自動採用します。
    未知のROMシリーズ名の場合だけ、手動選択に切り替えます。
    """
    if not ask_yes_no("アンテナ設定表示・接続チェックを実行しますか？ [y/N]: ", default=False):
        return None

    identified_model_key = identify_model_key_from_rom(rom_info) if rom_info is not None else None
    if rom_info is not None and not allows_4ch_sequential_inventory(rom_info.series_name):
        if identified_model_key in {"UTR-SUN02V-8CH", "UTR-SUN02-8CH"}:
            print("8CH機では4CH向けアンテナ切替処理を使用しません。8CHアンテナ制御は未対応です。")
        else:
            print("このROMシリーズ名では4CH向けアンテナ切替処理を使用しません。")
        return None

    if identified_model_key is not None:
        profile = get_model_profile(identified_model_key)
        print(f"ROMバージョンから仕様書上の機種を確定しました: {profile.display_name}")
        print("この機種プロファイルを自動採用します。")
    else:
        try:
            profile = prompt_for_antenna_model_profile(identified_model_key=None)
        except KeyboardInterrupt:
            return None

    print("")
    print("=== アンテナプロトコル確認 ===")
    print(f"対象機種: {profile.display_name}")
    print(profile.note)

    command_mode_setting: Optional[AntennaSwitchingSetting] = None
    flash_setting: Optional[AntennaSwitchingSetting] = None

    if profile.supports_antenna_switching_setting:
        print("")
        print("=== アンテナ切替設定の現在値（読み取りのみ） ===")
        command_mode_setting = read_and_print_antenna_switching_setting(ser, PARAMETER_KIND_COMMAND_MODE)
        flash_setting = read_and_print_antenna_switching_setting(ser, PARAMETER_KIND_FLASH)
    else:
        print("")
        print("この機種では、今回のPRではアンテナ切替設定 55 43 の自動読み取りを行いません。")
        print("理由: 8CH機や1CH機では、アンテナ切替設定と使用アンテナ番号の体系が異なるためです。")

    print("")
    connected_targets = check_and_print_antennas(ser, profile=profile)

    if profile.key != "UTR-SUN02-4CH":
        print("このPRでは、Inventory対象アンテナの一時変更はUTR-SUN02-4CHだけを対象にします。")
        return None

    if command_mode_setting is None or flash_setting is None:
        print("アンテナ切替設定を読み取れなかったため、Inventory対象アンテナは変更しません。")
        return None

    available_targets = filter_inventory_antenna_targets(
        connected_targets=connected_targets,
        flash_setting=flash_setting,
    )
    selected_targets = prompt_for_inventory_antenna_targets(available_targets)
    if not selected_targets:
        return None

    return InventoryAntennaSelection(
        restore_setting=command_mode_setting,
        selected_targets=selected_targets,
    )


def received_data_contains_nack(data: bytes) -> bool:
    """受信データの中にNACK応答が含まれるか確認します。

    Args:
        data (bytes): communicate() から返された受信データ。

    Returns:
        bool: NACKフレームが1つでも含まれていれば True、なければ False。

    補足:
        RFIDリーダライタからNACK応答が返った場合は、タグ未検出とは別扱いにします。
        アンテナ未接続などの異常を「タグがないだけ」と誤解しないようにするためです。
    """
    index = 0
    while index < len(data):
        if data[index] != STX[0]:
            index += 1
            continue

        data_frame, next_index = parse_data_frame(data, index)
        if data_frame is None:
            # 不完全なフレームはNACKとは判断しません。
            # ここで止めずに1バイト進めることで、後続データの確認を続けます。
            index += 1
            continue

        if verify_sum_value(data_frame) and data_frame[CMD_LOCATION] == NACK[0]:
            return True

        index = next_index

    return False


def select_buzzer_command_for_inventory_result(has_tag: bool, has_nack: bool = False) -> bytes:
    """Inventory結果に応じたブザーコマンドを返します。

    Args:
        has_tag (bool): タグを1枚以上読み取った場合は True。
        has_nack (bool): NACK応答を受信した場合は True。

    Returns:
        bytes: RFIDリーダライタへ送信するブザー制御コマンド。

    補足:
        NACKはタグ未検出より優先します。
        これは、アンテナ未接続などの異常を「タグが無いだけ」と誤認しないためです。
    """
    if has_nack:
        # NACK用ブザーは未知の固定バイト列を手書きせず、
        # 既存のフレーム生成関数でSUMまで計算して作ります。
        return build_buzzer_command(response_required=True, sound_type=BUZZER_SOUND_NACK)

    if has_tag:
        return COMMANDS['UHF_BUZZER_pipipi']

    return COMMANDS['UHF_BUZZER_pi']


def get_buzzer_success_message(has_tag: bool, has_nack: bool = False) -> str:
    """ブザー制御ACK受信時に表示する日本語メッセージを返します。"""
    if has_nack:
        return "NACK応答のため、ブザー通知を実行しました（NACK用ブザー: sound_type=0x02）"
    if has_tag:
        return "タグを検出したため、ブザー通知を実行しました（ピッピッピ）"
    return "タグ未検出のため、ブザー通知を実行しました（ピー）"


def should_stop_inventory_repeat(has_nack: bool) -> bool:
    """指定回数読み取りの途中で中断すべきかを返します。

    Args:
        has_nack (bool): 今回のInventory応答にNACKが含まれているか。

    Returns:
        bool: NACK時は True。呼び出し元は残りの繰り返し読み取りを中断します。

    補足:
        NACKは通信・接続条件の異常を示す可能性があるため、
        同じ条件で何度もInventoryを続けず、最初のNACKで止めます。
    """
    return has_nack


def play_buzzer_for_inventory_result(ser: serial.Serial, has_tag: bool, has_nack: bool = False) -> None:
    """Inventory結果に応じてブザー通知を実行します。

    Args:
        ser (serial.Serial): 接続済みのシリアル通信オブジェクト。
        has_tag (bool): タグを1枚以上読み取った場合は True。
        has_nack (bool): NACK応答を受信した場合は True。

    補足:
        NACK時はタグ未検出音ではなく、NACK用ブザー候補音を使用します。
        ただし sound_type=0x02 の実音は、実機で確認します。
    """
    buzzer_command = select_buzzer_command_for_inventory_result(has_tag=has_tag, has_nack=has_nack)
    buzzer_response = communicate(ser, buzzer_command)

    if re.match(STX + b'.' + ACK, buzzer_response):
        print(get_buzzer_success_message(has_tag=has_tag, has_nack=has_nack))
    elif re.match(STX + b'.' + NACK, buzzer_response):
        print_nack_message(buzzer_response)
    else:
        print("ブザー制御 ACK/NACK なし")


# メイン処理
def main():
    """
    プログラムのエントリポイント。
    シリアルポートの選択、リーダライタとの通信、コマンド実行、結果表示、集計保存を行う。
    """
    # --- 接続情報の入力 ---
    print("UTR（USBモデル）に接続します。")

    # 利用可能なシリアルポートを列挙
    ports = list_ports.comports()
    if not ports:
        print("利用可能なCOMポートが見つかりませんでした。")
        sys.exit(1)

    port_name = prompt_for_port_name(ports)

    baud_rate_str = input("ボーレートを入力してください（例: 19200, 115200, 未入力なら115200）: ")
    baud_rate = parse_baud_rate_input(baud_rate_str)

    # --- シリアルポート設定 ---
    ser: Optional[serial.Serial] = None
    try:
        # シリアルポートを開く (timeout=0 でノンブロッキング読み取り)
        ser = serial.Serial(
            port=port_name,
            baudrate=baud_rate,
            timeout=0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        ser.reset_input_buffer()  # 入力バッファをクリア
        ser.reset_output_buffer() # 出力バッファをクリア
        print(f"接続成功: {port_name} @ {baud_rate}bps")
    except serial.SerialException as e:
        print(f"シリアルポート接続エラー: {e}")
        sys.exit(1)

    # --- ROMバージョンで通信確認 ---
    # ROMバージョン確認コマンドを送信し、応答を待つ
    rom_info: RomVersionInfo | None = None
    result = communicate(ser, COMMANDS['ROM_VERSION_CHECK'])
    # 応答がACKで、詳細コマンドがROMバージョン確認のものであるかチェック
    if re.match(STX + b'.' + ACK, result):
        if bytes([result[DETAIL_LOCATION]]) == DETAIL_ROM:
            print("USB通信: OK（ROMバージョン ACK 受信）")
            try:
                rom_info = parse_rom_version_response(result)
                identified_model_key = identify_model_key_from_rom(rom_info)
                for line in format_rom_version_info(rom_info, identified_model_key=identified_model_key):
                    print(line)
            except ValueError as exc:
                print(f"ROMバージョンレスポンスの解析に失敗しました: {exc}")
                print("Raw:", result.hex().upper())
    # 応答がNACKの場合
    elif re.match(STX + b'.' + NACK, result):
        if bytes([result[DETAIL_LOCATION]]) == DETAIL_ROM:
            print_nack_message(result)
    # その他の応答の場合
    else:
        print("USB通信: NG（ACK/NACK なし）")
        ser.close()
        sys.exit(1)

    # --- コマンドモード切替 ---
    # コマンドモード設定コマンドを送信
    result = communicate(ser, COMMANDS['COMMAND_MODE_SET'])
    if re.match(STX + b'.' + ACK, result):
        print("コマンドモードに切り替えました")
    elif re.match(STX + b'.' + NACK, result):
        print_nack_message(result)
    else:
        print("コマンドモード切替に失敗しました")
        ser.close()
        sys.exit(1)

    # --- 出力/周波数の読み取り ---
    # 出力電力の読み取り
    result = communicate(ser, COMMANDS['UHF_READ_OUTPUT_POWER'])
    if re.match(STX + b'.' + ACK, result):
        # 応答から出力レベルを抽出し、dBmに変換して表示
        print("UHF_READ_OUTPUT_POWER response:", result.hex().upper())
        output_power_level = parse_output_power_dbm(result[7:9])
        print("送信出力値：", output_power_level, "dBm")
    elif re.match(STX + b'.' + NACK, result):
        print_nack_message(result)
    else:
        print("通信エラー（UHF_READ_OUTPUT_POWER）")
        print(result.hex())
        ser.close()
        sys.exit(1)

    # 周波数チャンネルの読み取り
    result = communicate(ser, COMMANDS['UHF_READ_FREQ_CH'])
    if re.match(STX + b'.' + ACK, result):
        # 応答からチャンネル番号を抽出し、対応する周波数を表示
        output_ch = result[7] # 8バイト目がチャンネル番号
        print("チャンネル番号：", output_ch, "ch")
        if 1 <= output_ch <= len(OUTPUT_CH_FREQ_LIST):
            print("送信周波数：", OUTPUT_CH_FREQ_LIST[output_ch-1], " MHz")
    elif re.match(STX + b'.' + NACK, result):
        print_nack_message(result)
    else:
        print("通信エラー（UHF_READ_FREQ_CH）")
        print(result.hex())
        ser.close()
        sys.exit(1)

    # --- インベントリパラメータ取得/設定（任意） ---
    # インベントリパラメータ取得コマンドを送信
    result = communicate(ser, COMMANDS['UHF_GET_INVENTORY_PARAM'])
    if re.match(STX + b'.' + ACK, result):
        print("UHF_GET_INVENTORY_PARAM が正常に実行されました")
    elif re.match(STX + b'.' + NACK, result):
        print_nack_message(result)
    else:
        print("UHF_GET_INVENTORY_PARAM 実行エラー")
        print(result.hex())
        ser.close()
        sys.exit(1)

    print("UHF_GET_INVENTORY_PARAM response:", result.hex().upper())
    inventory_param = parse_inventory_param_response(result)
    for line in format_inventory_param_response(inventory_param):
        print(line)
    print("UHF_SET_INVENTORY_PARAM は自動送信しません。設定変更は行いません。")

    # --- アンテナ設定表示・接続チェック（任意） ---
    # UHF_CheckAntennaは接続確認専用コマンドです。
    # ここではFLASHやRAMへの書き込みは行いません。
    antenna_selection = run_optional_antenna_check(ser, rom_info=rom_info)

    # --- 読み取りループ ---
    total_read_time   = 0.0 # 総読み取り時間
    total_read_count  = 0   # 総読み取りタグ数
    total_iterations  = 0   # 総繰り返し回数
    pc_uii_count_dict = {}  # PC+UIIごとの読み取り回数を格納する辞書
    inventory_result_item_dict = {}
    try:
        buzzer_enabled = ask_yes_no("読み取り結果をブザーで通知しますか？ [y/N]: ", default=False)
        mask_pc_uii_display = ask_yes_no("PC+UIIを画面表示でマスクしますか？ [y/N]: ", default=False)
        if mask_pc_uii_display:
            print("PC+UIIは画面表示のみ省略します。集計キーと結果ファイルには実値を保持します。")

        while True:
            try:
                repeat_count_str = input("繰り返す回数を入力してください（1〜100、終了は'q'）: ").strip()
                if repeat_count_str.lower() == 'q':
                    break # 'q'が入力されたらループを終了
                repeat_count = int(repeat_count_str)
                if not (1 <= repeat_count <= 100):
                    raise ValueError("1から100の範囲で入力してください")
            except ValueError as e:
                print(f"入力エラー: {e}。再度入力してください。")
                continue

            inventory_targets: list[AntennaCheckTarget | None] = [None]
            current_antenna_setting: Optional[AntennaSwitchingSetting] = None

            if antenna_selection is not None and antenna_selection.selected_targets:
                inventory_targets = list(antenna_selection.selected_targets)
                current_antenna_setting = antenna_selection.restore_setting

            total_iterations += repeat_count * len(inventory_targets)

            start_time = time.time()
            stop_current_request = False

            for _ in range(repeat_count):
                for inventory_target in inventory_targets:
                    if inventory_target is not None:
                        print("")
                        print(f"--- Inventory対象: {inventory_target.label}（{inventory_target.description}） ---")

                        if current_antenna_setting is None:
                            print("現在のアンテナ設定が不明なため、このアンテナのInventoryをスキップします。")
                            continue

                        updated_setting = write_command_mode_antenna_setting(
                            ser=ser,
                            current_setting=current_antenna_setting,
                            target=inventory_target,
                        )
                        if updated_setting is None:
                            print(f"{inventory_target.label}への切替に失敗したため、このアンテナのInventoryをスキップします。")
                            continue

                        current_antenna_setting = updated_setting

                    # UHFインベントリコマンドを送信します。
                    # NACKが返った場合は、アンテナ未接続などの異常が疑われるため、
                    # 残りの繰り返し読み取りを続けず、この入力回のInventoryを中断します。
                    result = communicate(ser, COMMANDS['UHF_INVENTORY'])
                    if result:
                        # NACK有無は、ブザー選択と繰り返し中断の判断に使います。
                        # received_data_parse() はNACK内容を表示しますが、戻り値にはNACK有無を含めないため、
                        # ここで別途、受信フレーム内のNACKを確認します。
                        has_nack = received_data_contains_nack(result)

                        # 受信データを解析し、PC+UIIリスト、RSSIリスト、期待される読み取り数を取得
                        pc_uii_list, rssi_list, expected_count, read_channel = received_data_parse(result)
                        if expected_count is not None:
                            print(f"読み取り完了レスポンス枚数: {expected_count} 枚")
                        if read_channel is not None:
                            print(f"読み取りチャンネル: {read_channel} ch")

                        for pc_uii, rssi_value in zip(pc_uii_list, rssi_list):
                            pc_uii_hex = pc_uii.hex().upper() # PC+UIIを16進数文字列に変換
                            print(f"PC+UII: {format_pc_uii_for_display(pc_uii_hex, mask=mask_pc_uii_display)}")
                            print(f"RSSI: {rssi_value:.1f} dBm")
                            pc_uii_count_dict[pc_uii_hex] = pc_uii_count_dict.get(pc_uii_hex, 0) + 1 # カウントを更新
                            antenna_number = inventory_target.number if inventory_target is not None else None
                            antenna_label = inventory_target.label if inventory_target is not None else None
                            antenna_description = inventory_target.description if inventory_target is not None else None
                            item_key = (pc_uii_hex, antenna_number, antenna_label, antenna_description)
                            if item_key not in inventory_result_item_dict:
                                inventory_result_item_dict[item_key] = {
                                    "antenna_number": antenna_number,
                                    "antenna_label": antenna_label,
                                    "antenna_description": antenna_description,
                                    "pc_uii": pc_uii_hex,
                                    "read_count": 0,
                                }
                            inventory_result_item_dict[item_key]["read_count"] += 1

                        total_read_count += len(pc_uii_list)

                        if buzzer_enabled:
                            play_buzzer_for_inventory_result(
                                ser,
                                has_tag=len(pc_uii_list) > 0,
                                has_nack=has_nack,
                            )

                        if should_stop_inventory_repeat(has_nack):
                            print("NACK応答を受信したため、指定回数の残り読み取りを中断します。")
                            stop_current_request = True
                            break
                    else:
                        print("インベントリ応答がありませんでした。")
                        if buzzer_enabled:
                            play_buzzer_for_inventory_result(ser, has_tag=False, has_nack=False)

                if stop_current_request:
                    break

            end_time = time.time()
            total_read_time += (end_time - start_time)

            print(f"現在の合計読み取り時間: {total_read_time:.2f} 秒")
            print(f"現在の合計読み取り枚数: {total_read_count} 枚")
    except KeyboardInterrupt:
        print("")
        print("中断要求を受け付けました。終了処理を行います。")
    except Exception as exc:
        print("")
        print("Inventory処理中にエラーが発生しました。終了処理を行います。")
        print(f"エラー内容: {exc}")
    finally:
        finish_inventory_session(
            ser,
            antenna_selection,
            total_iterations,
            total_read_time,
            total_read_count,
            pc_uii_count_dict,
            inventory_result_item_dict,
        )

if __name__ == '__main__':
    main()

