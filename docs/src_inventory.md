# `src/utr_usb_sample.py` 棚卸し

この資料は `src/utr_usb_sample.py` をテキストとして読んで整理したものです。実行、import、USB実機通信は行っていません。

## ファイルの役割

`src/utr_usb_sample.py` は、UTR-S201/202 系の RFID リーダライタを USBシリアル接続で操作するコマンドラインサンプルです。

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
| `handle_inventory_response` | インベントリ応答からPC/UIIとRSSIを抽出 | いいえ | いいえ | いいえ |
| `check_inventory_ack_response` | ACKフレームから読み取り予定枚数を取得 | いいえ | いいえ | いいえ |
| `parse_data_frame` | 受信バイト列から1フレームを切り出す | いいえ | いいえ | いいえ |
| `received_data_parse` | 複数フレームを走査し、インベントリ結果をまとめる | いいえ | いいえ | いいえ |
| `parse_nack_response` | NACKエラーコードをメッセージ化する | いいえ | いいえ | いいえ |
| `calculate_sum_value` | SUM値を計算する | いいえ | いいえ | いいえ |
| `verify_sum_value` | SUM値を検証する | いいえ | いいえ | いいえ |
| `convert_rssi` | RSSIの16進表現をdBm相当に変換する | いいえ | いいえ | いいえ |
| `save_results_to_file` | インベントリ集計結果をファイルへ追記する | いいえ | いいえ | はい |
| `main` | COM選択から実機通信、集計保存まで全体を実行する | はい | はい | はい |

## Todo コメントの一覧

ソース先頭の TODO には、今後の検討項目として以下の趣旨が書かれています。

- ACK/NACK判定を別関数化できる可能性
- 文字入力のチェック処理を別関数化できる可能性
- 送信出力の変更可否の検討
- 連続インベントリモード対応の検討
- アンテナ選択や設定変更の扱いの検討
- `OUTPUT_CH_FREQ_LIST` を辞書型にするかの検討
- レスポンスデータの詳細コマンド確認を強化する検討
- 経過時間の取得方法の検討

## 注意すべき処理

| 処理 | 注意点 |
|---|---|
| COMポート選択 | `list_ports.comports()` と `input()` に依存しており、自動テストしづらい |
| `communicate` 関数 | 実機I/O、タイムアウト、フレーム検証、ACK/NACK終了判定がまとまっている |
| SUM検証 | `calculate_sum_value` と `verify_sum_value` は分離済みで、単体テスト候補 |
| NACK解析 | `parse_nack_response` は単体テストしやすいが、実機ログとの突合も必要 |
| 送信出力の読み取り | `UHF_READ_OUTPUT_POWER` の応答バイト位置に依存している |
| 送信出力の書き込み | 現状は送信出力書き込みコマンドは見当たらないが、設定変更系コマンドは慎重に扱う |
| インベントリ処理 | 応答フレーム解析、読み取り枚数、PC/UII、RSSIが絡むため実機ログ比較が重要 |
| ブザー制御 | 実機に音を鳴らす副作用がある |
| 集計結果保存 | `inventory_results.txt` へ追記するため、実行時に作業ツリーへファイルが出る可能性がある |
