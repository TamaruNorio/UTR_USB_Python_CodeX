# Takaya UTR-S201/202 USB Sample (Python)

## プロジェクト概要

このリポジトリは、TAKAYA製 RFID リーダライタ UTR-S201/202 シリーズを USBシリアル接続で扱う Python サンプルです。

現在は、通常Inventory確認に加えて、UTR-SUN02-4CH のアンテナ順次Inventory、UTR-SUN02-8CH / USM08 の複数アンテナ順次Inventory確認CLIも含みます。

本サンプルは無保証で提供される確認用コードです。実際の運用環境で利用する場合は、機器設定、通信条件、プロトコル仕様、周辺環境を十分に確認してください。

## 現在の主な実行入口

### 標準Inventoryフロー

通常の実機確認は、以下を実行します。

```powershell
py .\src\utr_usb_sample.py
```

この標準入口では、次の流れで動作します。

1. USBシリアル接続する。
2. ROMバージョンを読み取り、仕様書上の機種を確認する。
3. コマンドモードへ切り替える。
4. 現在の送信出力設定を読み取る。
5. UTR-SUN02-4CH / USM02 の場合、Inventory中だけ送信出力を一時変更するか確認する。
6. 変更する場合は、コマンドモード用パラメータだけを書き換える。
7. Inventory前の送信出力設定、周波数設定、Inventoryパラメータを表示する。
8. 必要に応じて、UTR-SUN02-4CH のアンテナ接続確認とANT別順次Inventoryを実行する。
9. Inventoryを実行する。
10. 終了時に送信出力を元の値へ復元する。
11. アンテナ設定を変更した場合は、元のコマンドモード用アンテナ設定へ復元する。
12. 結果ファイルを保存し、シリアル接続を閉じる。

### UTR-SUN02-8CH 複数アンテナ順次Inventory確認CLI

UTR-SUN02-8CH / USM08 で、接続OKアンテナを選択順に切り替えてInventoryする場合は、以下を実行します。

```powershell
py .\src\utr_8ch_sequential_inventory_cli.py
```

このCLIでは、次の流れで動作します。

1. USBシリアル接続する。
2. ROMバージョンを読み取り、UTR-SUN02-8CH / USM08 であることを確認する。
3. コマンドモードへ切り替える。
4. Inventory前のリーダライタ設定を読み取り表示する。
5. `UHF_GET_INVENTORY_PARAM` を読み取り表示する。
6. 変更前の使用アンテナ番号を読み取り、終了時復元用に保持する。
7. 変更前設定を読み取れない場合は、順次Inventoryを開始しない。
8. ANT1〜ANT8の接続チェックを実行する。
9. 接続OKアンテナだけを候補表示する。
10. `1`、`1,3`、`all`、`q` の入力を受け付ける。
11. 選択した全ANTの使用アンテナ番号設定フレームを事前表示する。
12. 最初に1回だけ確認し、選択順に使用アンテナ番号設定を送信する。
13. ACKならそのANTでInventoryする。
14. NACKまたはACK/NACKなしなら、そのANTをスキップする。
15. ANT別に読み取り枚数、Inventory実行回数、スキップ回数を表示する。
16. 終了時に、開始前に読み取った使用アンテナ番号へ自動復元する。
17. Ctrl+Cや例外時も、可能な範囲でシリアルクローズ前に自動復元を試みる。
18. 必要に応じて、8CH順次InventoryサマリをCSV/JSONへ保存する。
19. シリアル接続を閉じる。

## 重要な制約

- USB接続は仮想COMポートとして扱います。
- 通信速度の標準確認値は 115200 bps です。
- 標準入口の送信出力一時変更は、現時点では UTR-SUN02-4CH / USM02 を対象にします。
- 送信出力の変更先は、コマンドモード用パラメータです。
- FLASHデータへの書き込みは行いません。
- `UHF_SET_INVENTORY_PARAM` は自動送信しません。
- UTR-SUN02-8CH / USM08 の順次Inventory CLIでは、使用アンテナ番号設定をコマンドモード用パラメータへ送信します。FLASHへは保存しません。
- UTR-SUN02-8CH / USM08 では、Inventory対象への一時切替時に ANT1=使用アンテナ番号 `00h`、ANT2=`20h`、ANT3=`40h`、ANT4=`60h`、ANT5=`80h`、ANT6=`A0h`、ANT7=`C0h`、ANT8=`E0h` を使います。
- ただし、開始前の変更前設定は外部アンテナ番号が `00h` 固定とは限りません。終了時は開始前に読み取った内部アンテナ番号・外部アンテナ番号へ自動復元します。
- UTR-SUN02V-8CH と UTR-SUN02-8CH はROMシリーズ名と機種識別までは扱いますが、UTR-SUN02-8CH用の実送信CLIは USM08 を対象にします。
- 実タグIDを含む `PC+UII` / `PC+EPC` は、GitHub、Issue、PR本文、公開ログへ載せません。
- 実行時に `PC+UIIを画面表示でマスクしますか？` で `y` を選ぶと、画面表示だけ `PC+UII: 省略` にできます。

## 現在の状態

- USB実機で ROM_VERSION_CHECK、COMMAND_MODE_SET、UHF_GET_INVENTORY_PARAM、UHF_INVENTORY、ブザー制御の応答を確認済みです。
- UTR-SUN02-4CH / USM02 で、送信出力の一時変更と復元を実機確認済みです。
- 送信出力 24.0 dBm から一時的に別出力へ変更し、Inventory後に 24.0 dBm へ復元できることを確認済みです。
- Inventory前に送信出力値、キャリア送信時間、キャリア休止時間、キャリアセンス待ち時間、周波数設定を表示できます。
- Inventory応答解析では、タグデータレスポンス、読み取り完了ACK、NACKを扱う補助処理を追加済みです。
- NACK応答時は、通常のタグ未検出とは分けて表示し、NACK用ブザー通知と繰り返しInventory中断に対応済みです。
- UTR-SUN02-4CHでは、UHF_CheckAntennaによるANT0〜ANT3接続確認、コマンドモード用アンテナ設定の読み取り、一時変更、終了時復元に対応済みです。
- UTR-SUN02-4CHでは、`0`、`1`、`0,1`、`all` 入力による複数アンテナの順次切替Inventoryに対応済みです。
- UTR-SUN02-8CH / USM08では、ANT1〜ANT8の接続チェック、接続OKアンテナの候補表示、`1`、`1,3`、`all`、`q` 入力による複数アンテナ順次Inventoryに対応済みです。
- UTR-SUN02-8CH / USM08では、ANT1とANT3接続状態で、`all` 選択による ANT1 -> ANT3 順次Inventoryを実機確認済みです。
- UTR-SUN02-8CH / USM08では、開始前に変更前の使用アンテナ番号を読み取り、通常終了時に変更前設定へ自動復元できることを実機確認済みです。
- 実機確認例では、開始前設定として `ANT3/EXT5`、使用アンテナ番号 `44h` を読み取り、終了時に `ANT3/EXT5 / 44h` へ自動復元できています。
- Ctrl+Cや例外時も、可能な範囲で `finally` 側から変更前設定へ自動復元を試みます。異常終了時の実機確認は別途実施してください。
- Inventory結果保存時、CSV/JSONへ `antenna_number`、`antenna_label`、`antenna_description` を保存します。
- 8CH順次Inventoryサマリ保存時、CSV/JSONへANT別のInventory実行回数、読み取り枚数、スキップ回数、復元結果を保存します。PC+UII実値は保存しません。
- Inventory未実行時は、結果ファイルを保存しません。
- 既存CSVのヘッダーが旧形式の場合は、`inventory_results_legacy_YYYYMMDD_HHMMSS.csv` に退避してから現行ヘッダーで保存します。
- pytest と GitHub Actions による確認運用を行っています。

## フォルダ構成

```text
UTR_USB_Python_CodeX/
├─ src/
│  ├─ utr_usb_sample.py
│  ├─ utr_usb_sample_legacy.py
│  ├─ utr_usb_inventory_with_output_power.py
│  ├─ utr_8ch.py
│  ├─ utr_8ch_single_antenna_inventory_cli.py
│  ├─ utr_8ch_sequential_inventory_cli.py
│  ├─ utr_output_power.py
│  ├─ utr_output_power_change.py
│  ├─ utr_output_power_temporary_change.py
│  ├─ utr_output_power_inventory_integration.py
│  ├─ utr_output_power_readout.py
│  ├─ utr_protocol.py
│  ├─ utr_inventory.py
│  ├─ utr_commands.py
│  ├─ utr_antenna.py
│  ├─ utr_serial_ports.py
│  ├─ utr_privacy.py
│  └─ utr_result_export.py
├─ tests/
├─ docs/
├─ scripts/
├─ requirements.txt
├─ requirements-dev.txt
└─ pytest.ini
```

## 主なファイル

| ファイル | 役割 |
|---|---|
| `src/utr_usb_sample.py` | 標準入口。送信出力一時変更つきInventoryフローを起動します。 |
| `src/utr_usb_sample_legacy.py` | 旧サンプル本体。既存関数・定数の互換維持用です。 |
| `src/utr_usb_inventory_with_output_power.py` | 送信出力一時変更つきInventoryフロー本体です。 |
| `src/utr_8ch.py` | 8CH機種判定、ANT番号変換、使用アンテナ番号設定フレーム生成補助関数です。 |
| `src/utr_8ch_single_antenna_inventory_cli.py` | UTR-SUN02-8CH向けの単一アンテナInventory確認CLIです。 |
| `src/utr_8ch_sequential_inventory_cli.py` | UTR-SUN02-8CH向けの複数アンテナ順次Inventory確認CLIです。 |
| `src/utr_output_power.py` | 送信出力値の dBm / raw値 / little-endian bytes 変換補助関数です。 |
| `src/utr_output_power_change.py` | 送信出力設定書き込みフレームの計画補助関数です。 |
| `src/utr_output_power_temporary_change.py` | 一時変更用フレームと復元用フレームをセットで作成します。 |
| `src/utr_output_power_inventory_integration.py` | Inventory前に送信出力一時変更を提案できるか判定します。 |
| `src/utr_output_power_readout.py` | 送信出力読み取りレスポンスからキャリア関連時間を解析します。 |
| `src/utr_protocol.py` | 実機通信なしのプロトコル補助関数です。 |
| `src/utr_inventory.py` | 実機通信なしのInventory解析補助関数です。 |
| `src/utr_commands.py` | コマンド定義とコマンド生成補助関数です。 |
| `src/utr_antenna.py` | アンテナ接続確認、アンテナ切替設定、機種プロファイル補助関数です。 |
| `src/utr_serial_ports.py` | COMポート選択補助関数です。 |
| `src/utr_privacy.py` | PC+UIIの画面表示・保存時マスク補助関数です。 |
| `src/utr_result_export.py` | Inventory集計結果のCSV/JSON保存補助関数です。 |
| `docs/` | 作業計画、確認手順、比較テンプレート、設計資料です。 |
| `scripts/dev_check.ps1` | ローカル開発確認スクリプトです。 |
| `scripts/git_preflight.ps1` | コミット/PR前の確認スクリプトです。 |

## セットアップ

Python仮想環境を使う場合の例です。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`py` が使えない環境では、利用可能な Python 実行コマンドに置き換えてください。

## 実行方法

### 標準Inventoryフロー

```powershell
py .\src\utr_usb_sample.py
```

実行後、画面の指示に従って以下を入力します。

1. COMポート番号またはCOM名。
2. ボーレート。未入力なら 115200 bps。
3. 送信出力をInventory中だけ一時変更するか。
4. 変更する場合は、変更後の送信出力値。
5. アンテナ設定表示・接続チェックを実行するか。
6. Inventory対象アンテナ。
7. ブザー通知の有無。
8. PC+UII画面表示マスクの有無。
9. Inventory繰り返し回数。
10. `q` で終了。

送信出力を一時変更した場合、終了時に元の送信出力へ復元します。

### UTR-SUN02-8CH 複数アンテナ順次Inventory

```powershell
py .\src\utr_8ch_sequential_inventory_cli.py
```

実行後、画面の指示に従って以下を入力します。

1. COMポート番号またはCOM名。
2. ボーレート。未入力なら 115200 bps。
3. 変更前の使用アンテナ番号読み取り結果を確認する。
4. 接続OKアンテナから、Inventory対象を `1`、`1,3`、`all`、`q` で選択する。
5. 表示された使用アンテナ番号設定フレームを確認する。
6. 順次Inventoryを開始する場合は `y` を入力する。
7. ブザー通知の有無を選ぶ。
8. PC+UII画面表示マスクの有無を選ぶ。
9. 選択ANT一巡の繰り返し回数を入力する。
10. `q` でInventoryループを終了する。
11. 終了時に、開始前に読み取った使用アンテナ番号へ自動復元されることを確認する。
12. 必要に応じて、8CH順次InventoryサマリをCSV/JSONへ保存する。

実機確認済みの例です。

```text
接続OK: ANT1, ANT3
選択: all
選択順: ANT1 -> ANT3
Inventory実行回数: 4
合計読み取り枚数: 172 枚
ANT1: 読み取り 8 枚 / Inventory実行 2 回 / スキップ 0 回
ANT3: 読み取り 164 枚 / Inventory実行 2 回 / スキップ 0 回
開始前設定: ANT3/EXT5 / 使用アンテナ番号 44h
最後に使用したANT: ANT3
自動復元完了: ANT3/EXT5 / 使用アンテナ番号 44h
```

## テスト実行

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

`git_preflight.ps1` は `git diff --check`、状態確認、差分表示、直近ログ表示、`dev_check` をまとめて実行します。

## ドキュメント

- [UHFリーダライタ開発者向け Quick Start](docs/uhf_reader_writer_programmer_quick_start.md)
- [送信出力一時変更CLI 実機確認手順](docs/output_power_temporary_change_cli_check.md)
- [送信出力一時変更つきInventory 実機確認手順](docs/inventory_with_temporary_output_power_check.md)
- [アンテナ選択・順次Inventory確認メモ](docs/antenna_selection_and_inventory.md)
- [UTR-SUN02-8CH 複数アンテナ順次Inventory確認手順](docs/8ch_sequential_inventory_cli_check.md)
- [UTRRWManager 8CH設定とPython制御の対応メモ](docs/utrrwmanager_8ch_settings_mapping.md)
- [RSSI検証計画](docs/rssi_validation_plan.md)
- [UTRRWManager比較テンプレート](docs/utr_rw_manager_comparison_template.md)
- [UHF Gen2 NACKエラー対応メモ](docs/nack_error_handling.md)
- [USB実機確認メモ](docs/usb_real_device_check_notes.md)
- [UHF Inventory応答解析メモ](docs/uhf_inventory_response_parsing.md)

## 実機確認前の注意

USB実機通信を行う前に、UTRRWManagerなどで接続条件と機器状態を事前確認してください。

- COMポートが認識されていることを確認する。
- サンプル実行時のCOMポート選択では、表示された番号または `COM6` のようなCOM名を入力できます。
- COMポート選択中に `q` を入力すると、接続前に終了できます。
- UTRシリーズのデフォルト通信速度は 115200 bps です。サンプル実行時、ボーレート未入力なら 115200 bps を使用します。
- 19200 bps 設定の機器を使う場合は、ボーレート入力で `19200` を明示入力してください。
- 機器設定を確認する。
- UTR機器の電源を確認する。
- アンテナ接続を確認する。
- RFタグを準備する。
- ROMバージョンを確認する。
- 送信出力設定を確認する。
- 送信出力値は `dBm * 10` を LSB/MSB の順で解析します。例: `F0 00` は `24.0 dBm` です。
- 実機通信は、手順と接続条件を確認したうえで行う。
- `UHF_SET_INVENTORY_PARAM` は自動送信しない。
- Inventory結果は `inventory_results.txt`、`inventory_results.csv`、`inventory_results.json` に保存されます。
- Inventoryを1回以上実行した場合は、タグ0枚でも結果を保存します。Inventory自体を実行していない場合は保存しません。
- CSVはExcelでの確認向け、JSONは後続処理やUTRRWManager結果との比較向けです。
- CSV/JSONには、取得できる場合は `antenna_number`、`antenna_label`、`antenna_description` も保存されます。
- 既存CSVのヘッダーが旧形式の場合は、旧CSVを `inventory_results_legacy_YYYYMMDD_HHMMSS.csv` に退避し、新しい `inventory_results.csv` を現行ヘッダーで作成します。
- `inventory_results.txt`、`inventory_results.csv`、`inventory_results.json`、`inventory_results_legacy_*.csv` はGit管理に入れないでください。
- 8CH順次Inventoryサマリは `8ch_sequential_inventory_summary.csv` と `8ch_sequential_inventory_summary.json` に保存できます。この2ファイルはGit管理に入れないでください。

## 送信出力一時変更の扱い

標準入口では、Inventory前に送信出力を一時変更するか確認します。

```text
送信出力をInventory中だけ一時変更しますか？ [y/N]: y
送信出力[dBm]: 20
この内容で一時変更してInventoryへ進みますか？ [y/N]: y
```

送信出力変更時の仕様は以下です。

- 変更対象はコマンドモード用パラメータです。
- FLASHは変更しません。
- 変更前に現在の送信出力値とキャリア関連時間を読み取ります。
- 変更用フレームと復元用フレームを生成します。
- 変更後に送信出力設定を読み戻します。
- Inventory終了時に元の送信出力へ復元します。
- 復元後にも送信出力設定を読み戻します。

## UTR-SUN02-4CHのアンテナ確認

UTR-SUN02-4CHでは、アンテナ設定表示・接続チェックを実行すると、ANT0〜ANT3の接続状態を確認できます。

- ANT0: 内蔵アンテナ
- ANT1〜ANT3: 外付けアンテナ
- Inventory対象アンテナとして `0`、`1`、`0,1`、`all` を入力できます。
- 複数アンテナ選択時は、同時使用ではなく、ANT0→ANT1のように順番に切り替えてInventoryします。
- アンテナ切替時もFLASHは変更しません。コマンドモード用パラメータだけを一時変更し、終了時に元の設定へ復元します。
- 8CH機はアンテナ番号体系が異なるため、4CH用の処理をそのまま流用しないでください。

## UTR-SUN02-8CHのアンテナ確認

UTR-SUN02-8CH / USM08では、専用CLIでANT1〜ANT8の接続状態を確認し、接続OKアンテナだけを順次Inventory対象にできます。

```powershell
py .\src\utr_8ch_sequential_inventory_cli.py
```

- UHF_CheckAntennaでは `00h`〜`07h` が ANT1〜ANT8 に対応します。
- Inventory対象への一時切替時は、ANT1=`00h`、ANT2=`20h`、ANT3=`40h`、ANT4=`60h`、ANT5=`80h`、ANT6=`A0h`、ANT7=`C0h`、ANT8=`E0h` を使います。
- 開始前に、変更前の使用アンテナ番号を読み取り、内部アンテナ番号と外部アンテナ番号を保持します。
- 開始前設定は、外部アンテナ番号 `00h` 固定とは限りません。実機確認では `ANT3/EXT5`、使用アンテナ番号 `44h` の例があります。
- 接続OKアンテナだけを候補表示します。
- Inventory対象アンテナとして `1`、`1,3`、`all`、`q` を入力できます。
- 複数アンテナ選択時は、同時使用ではなく、ANT1→ANT3のように順番に切り替えてInventoryします。
- 使用アンテナ番号設定は、コマンドモード用パラメータだけへ送信します。FLASHは変更しません。
- NACKまたはACK/NACKなしの場合、そのANTはスキップします。
- 終了時は、開始前に読み取った使用アンテナ番号へ自動復元します。
- Ctrl+Cや例外時も、可能な範囲でシリアルクローズ前に自動復元を試みます。

## セキュリティ・機密情報の注意

公開前に、以下の情報が含まれていないことを確認してください。

- 実IP
- 顧客名
- シリアル番号
- 未マスクの実測ログ
- 実測PC/UII または PC/EPC
- 認証情報、APIキー、トークン、パスワード

実機ログが必要な場合は、公開しても問題ないようにマスクした内容だけを使ってください。

共有用の例:

```text
PC+UII: 省略
RSSI: -xx.x dBm
```

## 今後の作業候補

- 標準Inventory側の送信出力一時変更について、変更送信後の復元保証をさらに強化する。
- ANT別の平均RSSI、最小RSSI、最大RSSI、読み取り成功率を集計する。
- UTRRWManager側ログとPython側ログを比較する。
- NACK/応答なし発生時のANT別エラー集計を強化する。
- Ctrl+Cや応答なしなど、異常終了時の実機確認結果を追加する。
- 実機確認結果を踏まえて、サンプルとドキュメントを継続更新する。

## ライセンス

このリポジトリのソースコードは MIT License の下で公開されています。詳細は [LICENSE](./LICENSE) を確認してください。
