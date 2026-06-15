# UTRRWManager Comparison Template

UTRRWManager と Python サンプルの結果を比較するための記入テンプレートです。

実測タグ ID、実シリアル番号、顧客情報、実 IP、未マスク実測ログは commit しないでください。サンプル行はマスク値だけを使います。

## 基本情報

| 項目 | 値 |
|---|---|
| date | `YYYY-MM-DD` |
| model | `UTR-S20x` |
| serial | `********` |
| customer | `社外非公開` |
| connection | `USB serial` |
| com_port | `COMx` |
| baudrate | `115200` |
| antenna | `masked antenna name` |
| tag_id | `E28011xxxxxxxxxxxxxx` |

## コマンド比較表

| コマンド | Python 受信 hex | Python 解析結果 | UTRRWManager 表示 | 一致/不一致 | 備考 |
|---|---|---|---|---|---|
| `ROM_VERSION_CHECK` | `AA BB xx xx` | `masked result` | `masked display` | `一致` | `sample only` |
| `UHF_INVENTORY` | `AA BB xx xx` | `tag_id=E28011xxxxxxxxxxxxxx` | `tag_id=E28011xxxxxxxxxxxxxx` | `一致` | `sample only` |

## RSSI 比較表

| 日付 | 機種 | タグ ID | 距離 | Python 表示 RSSI | UTRRWManager 表示 RSSI | 差分 | 備考 |
|---|---|---|---|---:|---:|---:|---|
| `YYYY-MM-DD` | `UTR-S20x` | `E28011xxxxxxxxxxxxxx` | `xx cm` | `-45.0` | `-45.0` | `0.0` | `masked sample` |

## Inventory パラメータ比較表

| 項目 | Python 解析結果 | UTRRWManager 表示 | 一致/不一致 | 備考 |
|---|---|---|---|---|
| `inventory_param_1` | `masked value` | `masked value` | `一致` | `sample only` |
| `inventory_param_2` | `masked value` | `masked value` | `一致` | `sample only` |

## ACK/NACK 比較表

| コマンド | Python 受信 hex | Python 解析結果 | UTRRWManager 表示 | 一致/不一致 | 備考 |
|---|---|---|---|---|---|
| `COMMAND_MODE_SET` | `AA BB xx xx` | `ACK` | `ACK` | `一致` | `sample only` |
| `UHF_INVENTORY` | `AA BB xx xx` | `NACK: masked reason` | `NACK: masked reason` | `一致` | `sample only` |

## 記録時の注意

- サンプル値は必ずマスク値に置き換える。
- 実タグ ID は `E28011xxxxxxxxxxxxxx` のように一部を伏せる。
- 実シリアル番号は `********` のように伏せる。
- 顧客名は `社外非公開` のように伏せる。
- RSSI の補正式は、このテンプレート上では決めない。
