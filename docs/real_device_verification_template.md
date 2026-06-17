# 実機確認ログテンプレート

このテンプレートは、UTR USB Pythonサンプルの実機確認結果を、GitHubのIssue、Pull Request、レビューコメントへ安全に共有するための記録フォーマットです。

## 1. 目的

実機確認時に、以下を再現しやすい形で残す。

- 使用機種
- ROMシリーズ
- 接続方式
- 確認した機能
- 実行結果
- エラー有無
- 次に確認すべき事項

同時に、以下の情報を公開ログへ含めないようにする。

- 実PC+UII / 実PC+EPC
- 実IPアドレス
- シリアル番号
- 顧客名
- 設置先名
- 認証情報
- 未マスクの実測ログ

## 2. 記録時の前提

このテンプレートは、公開リポジトリ上でも共有できる内容だけを書くことを前提にする。

実機確認で生成された以下のファイルは、GitHubへコミットしない。

```text
inventory_results.txt
inventory_results.csv
inventory_results.json
inventory_results_legacy_*.csv
*.log
```

実タグIDを含む可能性があるファイルは、ローカル環境または社内の安全な保管場所で管理する。

## 3. 実機確認サマリー

| 項目 | 内容 |
|---|---|
| 確認日 | YYYY-MM-DD |
| 確認者 | 例: Tamaru |
| 確認目的 | 例: ANT0/ANT1の順次Inventory確認 |
| 対象ブランチ | 例: main |
| 対象コミット | 例: xxxxxxx |
| Pythonバージョン | 例: Python 3.14.x |
| OS | 例: Windows 11 |
| 接続方式 | 例: USBシリアル |
| COMポート | 例: COMx |
| ボーレート | 例: 115200 bps |

## 4. 使用機器

| 項目 | 内容 |
|---|---|
| 機種 | 例: UTR-SUN02-4CH |
| ROMバージョン | 例: 2052USM02 |
| ROMシリーズ | 例: USM02 |
| 判定された機種名 | 例: UTR-SUN02-4CH |
| アンテナ構成 | 例: ANT0内蔵、ANT1外付け |
| 確認したアンテナ | 例: ANT0, ANT1 |

注意:

- シリアル番号は記載しない。
- 顧客設備名、設置先名、実IPアドレスは記載しない。
- 8CH機を確認した場合でも、4CH向けアンテナ切替処理を実行したとは書かない。実際に安全ガードで停止したことだけを記録する。

## 5. 実行前設定確認

Inventory前に表示された設定確認結果を、必要に応じてマスクして記録する。

| 項目 | 内容 |
|---|---|
| 送信出力設定読み取り | 成功 / 失敗 |
| 送信出力値 | 例: xx.x dBm |
| 周波数設定読み取り | 成功 / 失敗 |
| チャンネル番号 | 例: xx ch |
| 送信周波数 | 例: xxx.x MHz |
| Raw hex共有可否 | 原則として必要最小限。未確認情報を含む場合は共有しない |

記録例:

```text
=== Inventory前のリーダライタ設定（読み取りのみ） ===
送信出力値: xx.x dBm
送信出力Raw: 省略
チャンネル番号: xx ch
送信周波数: xxx.x MHz
周波数設定Raw: 省略
```

## 6. 確認した機能

該当するものにチェックを入れる。

- [ ] COMポート選択
- [ ] ROMバージョン読み取り
- [ ] ROMシリーズ判定
- [ ] 8CH誤操作防止ガード
- [ ] Inventory前の送信出力設定読み取り
- [ ] Inventory前の周波数設定読み取り
- [ ] アンテナ接続確認
- [ ] コマンドモード用アンテナ設定読み取り
- [ ] コマンドモード用アンテナ設定の一時変更
- [ ] ANT0 Inventory
- [ ] ANT1 Inventory
- [ ] ANT2 Inventory
- [ ] ANT3 Inventory
- [ ] 複数アンテナ順次Inventory
- [ ] PC+UII画面表示マスク
- [ ] RSSI表示
- [ ] Inventory結果保存
- [ ] Ctrl+C中断時のアンテナ設定復元
- [ ] 終了時のアンテナ設定復元
- [ ] 受信バッファクリア
- [ ] シリアル接続の正常終了

## 7. 実行結果

| 項目 | 結果 | 補足 |
|---|---|---|
| ROMバージョン読み取り | OK / NG | 例: USM02判定OK |
| 送信出力設定読み取り | OK / NG | 読み取り失敗時もInventory継続可 |
| 周波数設定読み取り | OK / NG | 読み取り失敗時もInventory継続可 |
| ANT0 Inventory | OK / NG / 未実施 | 例: 1枚読み取り |
| ANT1 Inventory | OK / NG / 未実施 | 例: 6枚読み取り |
| ANT2 Inventory | OK / NG / 未実施 | 例: アンテナ未接続 |
| ANT3 Inventory | OK / NG / 未実施 | 例: 未実施 |
| PC+UIIマスク | OK / NG / 未使用 | 例: `PC+UII: 省略` 表示 |
| アンテナ設定復元 | OK / NG / 不要 | 例: Ant0へ復元 |
| 結果ファイル保存 | OK / NG / 未実施 | ファイルはGit管理しない |
| 接続終了 | OK / NG | 例: 接続を閉じました |

## 8. 共有用ログ例

公開可能なログだけを貼る。

```text
--- Inventory対象: ANT0（内蔵アンテナ） ---
コマンドモード用アンテナ設定を一時変更します。
変更前: Ant1
変更後: ANT0（内蔵アンテナ）
FLASHは変更しません。
コマンドモード用アンテナ設定を一時変更しました。

読み取り完了レスポンス枚数: x 枚
読み取りチャンネル: xx ch
PC+UII: 省略
RSSI: -xx.x dBm

コマンドモード用アンテナ設定を元に戻します。
復元対象: Ant1
FLASHは変更していません。
コマンドモード用アンテナ設定を元に戻しました。
接続を閉じました。
```

## 9. 共有してはいけないログ例

以下は共有しない。

```text
PC+UII: 3000XXXXXXXXXXXXXXXXXXXXXXXX
PC+EPC: 3000XXXXXXXXXXXXXXXXXXXXXXXX
Serial: XXXXXXXXXX
IP: 192.168.xxx.xxx
Customer: 顧客名
Site: 設置先名
```

実タグIDが含まれる場合は、以下のように置き換える。

| 元の情報 | 共有時の表記 |
|---|---|
| 実PC+UII | `PC+UII: 省略` |
| 実PC+EPC | `PC+EPC: 省略` |
| 実IPアドレス | `192.168.xxx.xxx` |
| シリアル番号 | `省略` |
| 顧客名 | `顧客名省略` |
| 設置先名 | `設置先名省略` |

## 10. エラー記録

エラーが出た場合は、実タグIDや顧客情報を含まない範囲で記録する。

| 項目 | 内容 |
|---|---|
| 発生タイミング | 例: UHF_INVENTORY中 |
| エラー種別 | 例: NACK / タイムアウト / 予期しないレスポンス |
| 表示メッセージ | 例: アンテナ未接続の可能性 |
| Raw hex | 必要な場合のみ。実タグIDを含む可能性があれば省略 |
| 復旧操作 | 例: qで終了、アンテナ設定復元確認 |
| 再現性 | あり / なし / 未確認 |

## 11. PR本文貼り付け用テンプレート

```markdown
## Real Device Verification

Verified with masked field logs.

- Device: UTR-SUN02-4CH
- ROM series: USM02
- Connection: USB serial, COMx, 115200 bps
- Branch/commit: `<branch or commit>`
- Inventory target: ANT0 / ANT1 / ANT2 / ANT3 / all

### Results

- ROM version read: OK
- Output power readout before inventory: OK / NG / not tested
- Frequency readout before inventory: OK / NG / not tested
- 4CH antenna inventory safety guard: OK / not tested
- ANT0 inventory: OK / NG / not tested
- ANT1 inventory: OK / NG / not tested
- PC+UII display masking: OK / not used
- Antenna setting restore: OK
- Result files generated: OK / not generated
- Serial connection closed: OK

Actual PC+UII / PC+EPC values, serial numbers, customer names, and real IP addresses are omitted from this PR.
```

## 12. 確認後のローカル整理

実機確認後は、以下を確認する。

```powershell
git status --short
```

`inventory_results*` や `*.log` が出ている場合は、Gitへ追加しない。必要ならローカルの安全な場所へ退避する。

例:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "D:\Downloads\utr_inventory_check_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Get-ChildItem -Path . -Filter "inventory_results*" -File -ErrorAction SilentlyContinue |
    Move-Item -Destination $backupDir -Force
```

## 13. 完了条件

実機確認記録として有効と判断できる条件は以下。

- 実施環境が分かる。
- 何を確認したかが分かる。
- 成功・失敗が分かる。
- エラー時の状態が分かる。
- 実PC+UII / PC+EPCなどの機密情報を含まない。
- 次に再現確認できる。
