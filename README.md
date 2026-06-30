# Takaya UTR-S201 USB Sample (Python)

## プロジェクト概要

このリポジトリは、TAKAYA製 RFID リーダライタ UTR-S201 シリーズを USBシリアル接続で扱う Python サンプルです。

本サンプルは無保証で提供される確認用コードです。実運用で利用する場合は、機器設定、通信条件、プロトコル仕様、アンテナ接続、周辺環境を確認してください。

## 実行入口

通常使う入口は、原則として次の2つです。

### 1. 標準Inventoryフロー

```powershell
py .\src\utr_usb_sample.py
```

主な処理:

1. USBシリアル接続
2. ROMバージョン確認
3. コマンドモード切替
4. 送信出力、周波数、Inventoryパラメータの読み取り表示
5. UTR-SUN02-4CH / USM02 の送信出力一時変更確認
6. UTR-SUN02-4CH のアンテナ接続確認と順次Inventory
7. Inventory実行
8. 送信出力とアンテナ設定の復元
9. 結果ファイル保存
10. シリアル接続クローズ

### 2. UTR-SUN02-8CH 複数アンテナ順次Inventory確認CLI

```powershell
py .\src\utr_8ch_sequential_inventory_cli.py
```

主な処理:

1. USBシリアル接続
2. ROMバージョン確認
3. UTR-SUN02-8CH / USM08 判定
4. コマンドモード切替
5. Inventory前のリーダ設定表示
6. UHF_GET_INVENTORY_PARAM の読み取り表示
7. 開始前の使用アンテナ番号読み取り
8. ANT1〜ANT8の接続チェック
9. 接続OKアンテナから `1`、`1,3`、`all`、`q` で選択
10. 選択順に使用アンテナ番号設定とInventoryを実行
11. 終了時に開始前の使用アンテナ番号へ自動復元
12. 必要に応じてANT別サマリをCSV/JSON保存

## 重要な安全ルール

- FLASHデータへの書き込みは行いません。
- `UHF_SET_INVENTORY_PARAM` は自動送信しません。
- 周波数設定は変更しません。
- 送信出力の一時変更は、対象機種確認後、ユーザー確認を経て、コマンドモード用パラメータだけへ送信します。
- 8CH順次Inventoryでは、使用アンテナ番号設定をコマンドモード用パラメータだけへ送信します。FLASHへは保存しません。
- 8CH終了時は、開始前に読み取った内部アンテナ番号・外部アンテナ番号へ自動復元します。
- Ctrl+Cや例外時も、可能な範囲で `finally` 側から復元を試みます。
- 実タグIDを含む `PC+UII` / `PC+EPC` は、GitHub、Issue、PR本文、公開ログへ載せません。

## 現在の確認済み内容

### USB基本通信

- ROM_VERSION_CHECK
- COMMAND_MODE_SET
- UHF_GET_INVENTORY_PARAM
- UHF_INVENTORY
- ブザー制御
- NACK応答表示

### UTR-SUN02-4CH / USM02

確認済み:

```text
送信出力: 24.0 dBm -> 12.0 dBm -> 24.0 dBm
COM: COM6
ボーレート: 115200 bps
Inventory実行: あり
pytest: 234 passed
```

対応済み:

- 送信出力の一時変更
- 終了時の送信出力復元
- 復元後の読み戻し
- ANT0〜ANT3接続確認
- 複数アンテナ順次Inventory
- PC+UIIの画面表示マスク、結果ファイルマスク

### UTR-SUN02-8CH / USM08

確認済み:

```text
接続OK: ANT1, ANT3
選択: all
順序: ANT1 -> ANT3
開始前設定: ANT3/EXT5 / 使用アンテナ番号 44h
終了時復元: ANT3/EXT5 / 使用アンテナ番号 44h
```

対応済み:

- ANT1〜ANT8接続チェック
- 接続OKアンテナの候補表示
- `1`、`1,3`、`all`、`q` 入力
- 複数アンテナ順次Inventory
- ANT別読み取り枚数、Inventory実行回数、スキップ回数の集計
- 通常終了時の開始前設定復元
- Ctrl+Cや例外時の復元試行
- 復元前の受信バッファクリア
- 復元応答がACK/NACK以外の場合の1回再試行
- ANT別サマリCSV/JSON保存

未確認:

```text
8CH Ctrl+C時の最終復元成功ログ
送信出力一時変更中のCtrl+C復元
変更送信後、読み戻し例外発生時のfinally復元
```

## フォルダ構成

```text
UTR_USB_Python_CodeX/
├─ src/
│  ├─ utr_usb_sample.py
│  ├─ utr_usb_sample_legacy.py
│  ├─ utr_usb_inventory_with_output_power.py
│  ├─ utr_8ch.py
│  ├─ utr_8ch_antenna_diagnostics_cli.py
│  ├─ utr_8ch_sequential_inventory_cli.py
│  ├─ utr_antenna.py
│  ├─ utr_commands.py
│  ├─ utr_inventory.py
│  ├─ utr_output_power.py
│  ├─ utr_output_power_change.py
│  ├─ utr_output_power_inventory_integration.py
│  ├─ utr_output_power_readout.py
│  ├─ utr_output_power_temporary_change.py
│  ├─ utr_output_power_temporary_change_cli.py
│  ├─ utr_privacy.py
│  ├─ utr_protocol.py
│  ├─ utr_reader_settings.py
│  ├─ utr_result_export.py
│  └─ utr_serial_ports.py
├─ docs/
├─ scripts/
├─ tests/
├─ requirements.txt
├─ requirements-dev.txt
└─ pytest.ini
```

## 主なファイルの役割

| ファイル | 役割 |
|---|---|
| `src/utr_usb_sample.py` | 標準入口。通常はこのファイルを実行します。 |
| `src/utr_usb_sample_legacy.py` | 旧サンプル由来の既存関数群です。現時点では標準入口から読み込まれるため削除しません。 |
| `src/utr_usb_inventory_with_output_power.py` | 送信出力一時変更つきInventoryフロー本体です。 |
| `src/utr_8ch.py` | 8CH機種判定、ANT番号変換、使用アンテナ番号設定フレーム生成補助です。 |
| `src/utr_8ch_antenna_diagnostics_cli.py` | 8CH読み取り専用アンテナ診断CLIです。現時点では診断用として残します。 |
| `src/utr_8ch_sequential_inventory_cli.py` | 8CH複数アンテナ順次Inventoryの正式入口です。単一アンテナ選択もこのCLIで扱います。 |
| `src/utr_antenna.py` | アンテナ接続確認、アンテナ切替設定、機種プロファイル補助です。 |
| `src/utr_commands.py` | コマンド定義とフレーム生成補助です。 |
| `src/utr_inventory.py` | Inventory応答解析補助です。 |
| `src/utr_output_power.py` | 送信出力値の dBm / raw値 / little-endian bytes 変換補助です。 |
| `src/utr_output_power_change.py` | 送信出力設定書き込みフレームの計画補助です。 |
| `src/utr_output_power_inventory_integration.py` | Inventory前に送信出力一時変更を提案できるか判定します。 |
| `src/utr_output_power_readout.py` | 送信出力読み取りレスポンスからキャリア関連時間を解析します。 |
| `src/utr_output_power_temporary_change.py` | 一時変更用フレームと復元用フレームをセットで作成します。 |
| `src/utr_output_power_temporary_change_cli.py` | 送信出力一時変更単体確認CLIです。現状は共通ヘルパーも含むため削除しません。 |
| `src/utr_privacy.py` | PC+UIIの画面表示・保存時マスク補助です。 |
| `src/utr_protocol.py` | フレーム、SUM、NACKなどのプロトコル補助です。 |
| `src/utr_reader_settings.py` | リーダ設定表示補助です。 |
| `src/utr_result_export.py` | Inventory結果のCSV/JSON保存補助です。 |
| `src/utr_serial_ports.py` | COMポート選択補助です。 |

## セットアップ

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## テスト

pytestを直接実行する場合:

```powershell
py -m pytest
```

開発チェックをまとめて実行する場合:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev_check.ps1
```

コミットやPR前の確認を行う場合:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/git_preflight.ps1
```

## 結果ファイル

Inventory結果は以下に保存されます。

```text
inventory_results.txt
inventory_results.csv
inventory_results.json
```

8CH順次Inventoryサマリは以下に保存できます。

```text
8ch_sequential_inventory_summary.csv
8ch_sequential_inventory_summary.json
```

これらの結果ファイルはGit管理に入れないでください。

## ドキュメント

- [UHFリーダライタ開発者向け Quick Start](docs/uhf_reader_writer_programmer_quick_start.md)
- [送信出力一時変更CLI 実機確認手順](docs/output_power_temporary_change_cli_check.md)
- [送信出力一時変更つきInventory 実機確認手順](docs/inventory_with_temporary_output_power_check.md)
- [アンテナ選択・順次Inventory確認メモ](docs/antenna_selection_and_inventory.md)
- [UTR-SUN02-8CH 複数アンテナ順次Inventory確認手順](docs/8ch_sequential_inventory_cli_check.md)
- [UTRRWManager 8CH設定とPython制御の対応メモ](docs/utrrwmanager_8ch_settings_mapping.md)
- [UHF Gen2 NACKエラー対応メモ](docs/nack_error_handling.md)
- [USB実機確認メモ](docs/usb_real_device_check_notes.md)
- [UHF Inventory応答解析メモ](docs/uhf_inventory_response_parsing.md)

## 実機確認前の注意

- UTRRWManagerなどで、接続条件と機器状態を事前確認してください。
- COMポート、ボーレート、電源、アンテナ接続、タグ位置を確認してください。
- UTRシリーズの標準確認ボーレートは 115200 bps です。
- 19200 bps設定の機器を使う場合は、実行時に `19200` を明示入力してください。
- 実測PC/UII、シリアル番号、顧客名、IPアドレス、未マスクのログをGitHubへ載せないでください。

## 今後の作業候補

- 8CH Ctrl+C時の最終復元成功ログを取得する。
- 送信出力一時変更中のCtrl+C時の復元確認を行う。
- `src/utr_output_power_temporary_change_cli.py` から共通ヘルパーを分離し、CLI整理を検討する。
- `src/utr_usb_sample_legacy.py` の依存を段階的に解消し、将来的な削除を検討する。
- READMEが再び肥大化した場合は、詳細説明をdocsへ分離する。

## ライセンス

このリポジトリのソースコードは MIT License の下で公開されています。詳細は [LICENSE](./LICENSE) を確認してください。
