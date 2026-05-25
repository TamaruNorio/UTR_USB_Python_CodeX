# UTRRWManager 比較チェックリスト

このチェックリストは、Pythonサンプルと UTRRWManager の動作を比較するためのものです。

実機確認時は、Python側ログと UTRRWManager側ログを同じ条件で取得し、差分を確認します。

| 比較項目 | Python側で確認すること | UTRRWManager側で確認すること | メモ |
|---|---|---|---|
| COMポート | 使用している COMポート番号 | 同じ COMポート番号を選択しているか | 例: COM3 |
| 通信速度 | pyserial の baudrate 設定 | UTRRWManager の通信速度設定 | 値が一致しているか |
| ROMバージョン確認 | ROMバージョン取得コマンドの応答 | ROMバージョン表示 | 同じ機器を見ているか確認 |
| コマンドモード移行 | コマンドモード移行の成功/失敗 | コマンドモード状態 | NACK の有無も確認 |
| 送信出力読み取り | 読み取った送信出力値 | UTRRWManager上の送信出力値 | 書き換えは行わない |
| 周波数チャンネル読み取り | 読み取ったチャンネル情報 | UTRRWManager上のチャンネル情報 | 地域設定にも注意 |
| インベントリ実行 | インベントリコマンドの応答 | インベントリ結果 | 同じタグ条件で比較 |
| 読み取り枚数 | Pythonログ上のタグ枚数 | UTRRWManager上のタグ枚数 | 複数タグ時は特に確認 |
| PC/UIIデータ | PC/UII のバイト列や文字列表現 | UTRRWManager上の PC/UII 表示 | 表示形式の違いに注意 |
| RSSI | Pythonログ上の RSSI | UTRRWManager上の RSSI | 単位や符号の扱いを確認 |
| NACKエラー | NACK応答の有無と内容 | UTRRWManagerのエラー表示 | コマンド条件を合わせる |
| アンテナ未接続エラー | アンテナ未接続時の応答 | UTRRWManagerのエラー表示 | 意図的な確認は安全に実施 |

## 比較時の進め方

1. UTRRWManagerで通信できることを先に確認します。
2. Pythonサンプルでは、同じ COMポートと通信条件を使います。
3. Python側ログと UTRRWManager側ログを保存します。
4. 上の表に沿って、値やエラー表示が一致するか確認します。
