# `src/utr_usb_sample.py` リファクタリング候補

この資料は今後 `src/utr_usb_sample.py` を整理する場合の候補です。今回は実際のリファクタリングは行いません。

## すぐに分離できそうな処理

| 候補 | 理由 | テストしやすさ |
|---|---|---|
| SUM計算 | `calculate_sum_value` は入出力が単純 | 高い |
| SUM検証 | `verify_sum_value` はフレームbytesだけで確認可能 | 高い |
| NACK解析 | `parse_nack_response` はNACKフレームから文字列を返す | 高い |
| RSSI変換 | `convert_rssi` は16進文字列から数値への変換 | 高い |
| レスポンスフレーム解析 | `parse_data_frame` はbytesとindexだけで確認可能 | 中 |

## 慎重に扱うべき処理

| 処理 | 慎重に扱う理由 |
|---|---|
| `communicate` 関数 | 実機通信、タイムアウト、受信バッファ、SUM検証、ACK/NACK判定がまとまっている |
| Inventoryレスポンス解析 | タグ枚数、PC/UII、RSSI、ACKフレームの整合確認が絡む |
| 送信出力設定 | 誤って設定を書き換えると実機状態に影響する可能性がある |
| COMポート選択 | Windows環境、接続状態、ユーザー入力に依存する |

## 後回しにした方がよい処理

| 処理 | 後回しにする理由 |
|---|---|
| GUI化 | 現在の目的はCLIサンプルの整理であり、範囲が大きくなる |
| CSV保存形式の変更 | 出力互換性や利用者の運用に影響する可能性がある |
| 実機依存の通信処理変更 | 実機ログ比較なしでは安全性を判断しにくい |

## テストしやすい関数候補

- `calculate_sum_value`
- `verify_sum_value`
- `convert_rssi`
- `parse_nack_response`
- `parse_data_frame`
- `check_inventory_ack_response`
- `handle_inventory_response`
- `received_data_parse`

これらは、基本的に bytes や文字列を入力して戻り値やリスト更新を確認できます。実機を使わない単体テストから着手しやすい候補です。

## 実機がないと確認しづらい関数候補

- `communicate`
- `main`
- COMポート列挙と選択処理
- ROMバージョン確認
- コマンドモード移行
- 送信出力読み取り
- 周波数チャンネル読み取り
- インベントリ実行
- ブザー制御
- 集計結果保存を含む一連の実行フロー

特に `communicate` と `main` は、実機、COMポート、タイムアウト、ACK/NACK応答に依存します。Phase 3 の UTRRWManager比較ログを準備してから扱うのが安全です。

## Phase 3以降での推奨作業順

| 順番 | 作業 | 目的 |
|---|---|---|
| 1 | UTRRWManagerとPythonの実機ログ比較項目を確定する | 期待動作を先に固定する |
| 2 | SUM計算、SUM検証、RSSI変換、NACK解析の単体テストを追加する | 実機不要の安全な範囲から固める |
| 3 | レスポンスフレーム解析のサンプルデータを作る | Inventory解析の土台を作る |
| 4 | `communicate` の責務を送信、受信、検証に分ける設計を作る | 実装変更前に影響範囲を明確にする |
| 5 | 実機ログを使って Inventoryレスポンス解析を確認する | PC/UII、RSSI、読み取り枚数の整合を確認する |
| 6 | 送信出力設定やCOMポート選択は最後に扱う | 実機状態への影響があるため慎重に進める |

## 今回は行わないこと

- `src/utr_usb_sample.py` の変更
- `src/utr_usb_sample.py` の実行または import
- USB実機通信
- 送信出力など実機設定の変更
