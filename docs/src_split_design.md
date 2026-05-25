# `src/utr_usb_sample.py` 分割設計案

この資料は、将来 `src/utr_usb_sample.py` を分割する場合の設計案です。今回はソース分割や実装変更は行いません。

## 分割候補

| ファイル名 | 役割 | 移動候補の関数/定数 | 実機通信の有無 | テストしやすさ | リスク | 備考 |
|---|---|---|---|---|---|---|
| `src/utr_protocol.py` | STX/ETX/CR/SUMなどの通信フレーム共通処理 | `HEADER_LENGTH`, `FOOTER_LENGTH`, `STX`, `ADD`, `ETX`, `CR`, `ACK`, `NACK`, `CMD_LOCATION`, `DETAIL_LOCATION`, `DETAIL_ROM`, `DETAIL_INV`, `calculate_sum_value`, `verify_sum_value`, `parse_data_frame`, `parse_nack_response` | なし | 高い | 定数移動時のimport循環 | 最初に切り出す候補 |
| `src/utr_inventory.py` | Inventoryレスポンス解析 | `INV`, `handle_inventory_response`, `check_inventory_ack_response`, `received_data_parse`, `convert_rssi` | なし | 中から高 | フレーム仕様やRSSI仕様の理解不足 | `utr_protocol.py` に依存 |
| `src/utr_usb_transport.py` | pyserial接続と送受信 | `communicate`, COMポート選択補助、タイムアウト処理 | あり | 低い | 実機依存、タイムアウト、受信バッファ | 実機確認前は大きく触らない |
| `src/utr_commands.py` | コマンド定義と生成 | `COMMANDS`, `OUTPUT_CH_FREQ_LIST`, コマンド生成、送信出力読み取り/書き込みコマンド、ブザーコマンド生成 | 送信自体はなし | 中 | 固定bytesの意味を誤る可能性 | 要プロトコル仕様書確認 |
| `src/utr_cli.py` | CLI操作と画面表示 | `main`, ユーザー入力、表示、結果保存呼び出し | あり | 低い | ユーザー入力、実機通信、ファイル出力が絡む | 最後に整理する候補 |
| `src/utr_usb_sample.py` | 互換用エントリーポイント | `main` 呼び出しだけを残す案 | あり | 低い | 既存利用者への影響 | CLI互換を保つため残す |

## 依存方向の案

```text
utr_usb_sample.py
  -> utr_cli.py
      -> utr_usb_transport.py
      -> utr_commands.py
      -> utr_inventory.py
          -> utr_protocol.py
      -> utr_protocol.py
```

`utr_protocol.py` は最下層に置き、実機通信やユーザー入力に依存しないようにします。`utr_usb_transport.py` は pyserial 依存を集約し、`utr_cli.py` は人間向けの入力と表示を担当します。

## 設計上の注意

- まず純粋関数を分離し、pytestで守れる範囲を広げます。
- `communicate()` は実機通信とタイムアウト処理が含まれるため、早い段階で大きく変更しません。
- `COMMANDS` の固定bytesは意味を断定せず、要プロトコル仕様書確認の箇所を残します。
- `src/utr_usb_sample.py` は既存利用者向けの互換エントリーポイントとして残す案が安全です。
- 実機通信確認前に、送信出力書き込み系やタグ書き込み系の処理は不用意に実行しません。
