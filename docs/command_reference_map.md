# コマンド対応表

この資料は、`src/utr_usb_sample.py` 内の `COMMANDS` と、今後UTRRWManagerで比較する操作項目を対応付けるためのものです。今回は実機通信を行わず、実測値は記入しません。

| Python側キー名 | 用途 | 実機通信の有無 | UTRRWManagerで比較すべき操作 | レスポンスで確認すべき内容 | 注意点 |
|---|---|---|---|---|---|
| `ROM_VERSION_CHECK` | ROMバージョン確認 | あり | ROMバージョン確認 | ACK/NACK、ROMバージョン情報 | 実機確認時にログを保存 |
| `COMMAND_MODE_SET` | コマンドモード移行 | あり | コマンドモード確認 | ACK/NACK、モード移行成功/失敗 | 要プロトコル仕様書確認 |
| `UHF_INVENTORY` | RFタグのInventory実行 | あり | Inventory実行 | 読み取り枚数、PC/UII、RSSI | タグ条件をUTRRWManager側と揃える |
| `UHF_GET_INVENTORY_PARAM` | Inventoryパラメータ取得 | あり | Inventoryパラメータ確認 | ACK/NACK、取得パラメータ | 要プロトコル仕様書確認 |
| `UHF_SET_INVENTORY_PARAM` | Inventoryパラメータ設定 | あり | 設定内容の確認 | ACK/NACK、設定反映結果 | 書き込み系。実機確認では不用意に実行しない |
| `UHF_READ_OUTPUT_POWER` | 送信出力読み取り | あり | 送信出力読み取り | ACK/NACK、送信出力値 | 読み取り専用として扱い、書き込みと分ける |
| `UHF_READ_FREQ_CH` | 周波数チャンネル読み取り | あり | 周波数チャンネル読み取り | ACK/NACK、チャンネル番号、周波数 | `OUTPUT_CH_FREQ_LIST`との対応確認 |
| `UHF_BUZZER_pi` | ブザー制御、単音側 | あり | ブザー制御 | ACK/NACK、ブザー動作 | 実機に音が出るため明示許可後のみ |
| `UHF_BUZZER_pipipi` | ブザー制御、連続音側 | あり | ブザー制御 | ACK/NACK、ブザー動作 | 実機に音が出るため明示許可後のみ |
| `UHF_WRITE` | RFタグ書き込み用の例 | あり | 原則比較対象外 | 要プロトコル仕様書確認 | 現状使っていないコマンド。不用意に実行しない |

## 送信出力に関する注意

- 送信出力の読み取りと書き込みは明確に分けること。
- `UHF_READ_OUTPUT_POWER` は読み取り用途として扱うこと。
- 送信出力を書き換える処理は、実機状態へ影響する可能性があるため、明示許可と手順確認なしに行わないこと。

## 仕様確認が必要な箇所

- `COMMAND_MODE_SET` の詳細パラメータ
- `UHF_GET_INVENTORY_PARAM` のレスポンス詳細
- `UHF_SET_INVENTORY_PARAM` の設定値の意味
- `UHF_WRITE` の用途、対象メモリ、書き込み条件
- NACKコードと表示メッセージの完全対応
