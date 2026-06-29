# `src/utr_usb_sample.py` 棚卸し

この資料は `src/utr_usb_sample.py` をテキストとして読んで整理したものです。実行、import、USB実機通信は行っていません。

## ファイルの役割

`src/utr_usb_sample.py` は、UTR-S201 系の RFID リーダライタを USBシリアル接続で操作するコマンドラインサンプルです。

主な処理は、COMポート選択、シリアル接続、ROMバージョン確認、コマンドモード移行、送信出力と周波数チャンネルの読み取り、インベントリ実行、RSSI/PC/UII解析、ブザー制御、集計結果保存です。

## 使用している主なモジュール

| モジュール | 用途 |
|---|---|
| `sys` | 異常時の終了 |
| `time` | タイムアウト計測、待機 |
| `datetime` | 集計結果保存時の日時出力 |
| `re` | ACK/NACK応答の簡易判定 |
| `serial` | USBシリアル通信 |
| `serial.tools.list_ports` | 利用可能なCOMポート一覧取得 |
| `typing` | 型ヒント |

## 定数一覧の概要

| 定数 | 概要 |
|---|---|
| `COMMANDS` | 送信する固定コマンドの辞書 |
| `HEADER_LENGTH` | フレームヘッダ長 |
| `FOOTER_LENGTH` | フレームフッタ長 |
| `STX` / `ETX` / `CR` | フレーム開始、終了、終端バイト |
| `ADD` | リーダライタアドレス |
| `ACK` / `NACK` | 正常応答、エラー応答 |
| `INV` | インベントリ応答コマンド |
| `BUZ` | ブザー制御コマンド |
| `CMD_LOCATION` | フレーム内のコマンド位置 |
| `DETAIL_LOCATION` | フレーム内の詳細コマンド位置 |
| `DETAIL_ROM` | ROMバージョン確認の詳細コマンド |
| `DETAIL_INV` | インベントリの詳細コマンド |
| `OUTPUT_CH_FREQ_LIST` | 周波数チャンネルとMHzの対応表 |

## `COMMANDS` のコマンド一覧

| コマンド名 | 目的 | 注意 |
|---|---|---|
| `ROM_VERSION_CHECK` | ROMバージョン確認 | 実機通信で使用 |
| `COMMAND_MODE_SET` | コマンドモード移行 | 実機通信で使用 |
| `UHF_INVENTORY` | RFタグのインベントリ実行 | 実機通信で使用 |
| `UHF_GET_INVENTORY_PARAM` | インベントリ設定読み取り | 実機通信で使用 |
| `UHF_SET_INVENTORY_PARAM` | インベントリ設定書き込み | 設定変更を伴うため慎重に扱う |
| `UHF_READ_OUTPUT_POWER` | 送信出力読み取り | 実機通信で使用 |
| `UHF_READ_FREQ_CH` | 周波数チャンネル読み取り | 実機通信で使用 |
| `UHF_BUZZER_pi` | ブザー制御、単音側 | 実機通信で使用 |
| `UHF_BUZZER_pipipi` | ブザー制御、連続音側 | 実機通信で使用 |
| `UHF_WRITE` | RFタグ書き込み用の例 | 現状サンプル内では未使用 |

## 関数一覧

| 関数 | 目的 | 実機通信 | ユーザー入力 | ファイル出力 |
|---|---|---:|---:|---:|
| `communicate` | コマンド送信、レスポンス受信、フレーム検証 | はい | いいえ | いいえ |
