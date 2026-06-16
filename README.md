# Takaya UTR-S201/202 USB Sample (Python)

## プロジェクト概要

このリポジトリは、TAKAYA製 RFID リーダライタ UTR-S201/202 シリーズを USBシリアル接続で扱う Python サンプルです。

本サンプルは無保証で提供される確認用コードです。実際の運用環境で利用する場合は、機器設定、通信条件、プロトコル仕様、周辺環境を十分に確認してください。

## このリポジトリの位置づけ

このリポジトリでは、USBシリアル接続サンプルをベースに、実機通信を伴わずに確認できるプロトコル処理、Inventory解析、コマンド生成処理、アンテナ制御補助処理を分離しています。

## 現在の状態

- USB実機で ROM_VERSION_CHECK、COMMAND_MODE_SET、UHF_GET_INVENTORY_PARAM、UHF_INVENTORY、ブザー制御の応答を確認済みです。
- Inventory応答解析では、タグデータレスポンス、読み取り完了ACK、NACKを扱う補助処理を追加済みです。
- NACK応答時は、通常のタグ未検出とは分けて表示し、NACK用ブザー通知と繰り返しInventory中断に対応済みです。
- UTR-SUN02-4CHでは、UHF_CheckAntennaによるANT0〜ANT3接続確認、コマンドモード用アンテナ設定の読み取り、一時変更、終了時復元に対応済みです。
- UTR-SUN02-4CHでは、`0`、`1`、`0,1`、`all` 入力による複数アンテナの順次切替Inventoryに対応済みです。
- FLASH書き込みは行いません。アンテナ切替時は、コマンドモード用パラメータだけを一時変更します。
- 実機通信を伴わない純粋関数モジュールを追加済みです。
- pytest は `95 passed` の状態です。
- PowerShell 7 環境で、Codex Actions、`scripts/dev_check.ps1`、`scripts/git_preflight.ps1` による確認運用を整備済みです。

追加済みの主な純粋関数モジュールは以下です。

- `src/utr_protocol.py`: フレーム、SUM、NACKなどのプロトコル補助処理。
- `src/utr_inventory.py`: RSSI変換、Inventory応答解析補助。
- `src/utr_commands.py`: コマンド定義、フレーム生成、ブザーコマンド生成、アンテナ設定コマンド生成。
- `src/utr_antenna.py`: ROMバージョン照合、機種プロファイル、アンテナ接続確認、アンテナ切替設定レスポンス解析。

## フォルダ構成

```text
UTR_USB_Python/
├─ src/
│  ├─ utr_usb_sample.py
│  ├─ utr_protocol.py
│  ├─ utr_inventory.py
│  ├─ utr_commands.py
│  ├─ utr_antenna.py
│  ├─ utr_serial_ports.py
│  └─ utr_result_export.py
├─ tests/
│  ├─ test_smoke.py
│  ├─ test_protocol_helpers.py
│  ├─ test_commands.py
│  ├─ test_antenna_helpers.py
│  ├─ test_buzzer_helpers.py
│  ├─ test_nack_helpers.py
│  ├─ test_result_export.py
│  ├─ test_serial_port_helpers.py
│  └─ test_usb_sample_imports.py
├─ docs/
├─ scripts/
├─ requirements.txt
├─ requirements-dev.txt
└─ pytest.ini
```

## 主なファイル

| ファイル | 役割 |
|---|---|
| `src/utr_usb_sample.py` | USBシリアル接続用サンプル |
| `src/utr_protocol.py` | 実機通信なしのプロトコル補助関数 |
| `src/utr_inventory.py` | 実機通信なしのInventory解析補助関数 |
| `src/utr_commands.py` | コマンド定義とコマンド生成補助関数 |
| `src/utr_antenna.py` | アンテナ接続確認、アンテナ切替設定、機種プロファイル補助関数 |
| `src/utr_serial_ports.py` | COMポート選択補助関数 |
| `src/utr_result_export.py` | Inventory集計結果のCSV/JSON保存補助関数 |
| `tests/test_protocol_helpers.py` | プロトコル/Inventory補助関数のpytest |
| `tests/test_commands.py` | コマンド定義/生成関数のpytest |
| `tests/test_antenna_helpers.py` | アンテナ関連コマンド生成/レスポンス解析のpytest |
| `tests/test_usb_sample_imports.py` | CLIサンプル側import漏れ防止と入力解析のpytest |
| `docs/` | 作業計画、確認手順、比較テンプレート、設計資料 |
| `scripts/dev_check.ps1` | ローカル開発確認 |
| `scripts/git_preflight.ps1` | コミット/PR前の確認 |

## セットアップ

Python仮想環境を使う場合の例です。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`py` が使えない環境では、利用可能な Python 実行コマンドに置き換えてください。

## テスト実行

pytestを直接実行する場合:

```powershell
python -m pytest
```

開発チェックをまとめて実行する場合:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev_check.ps1
```

コミットやPR前の確認を行う場合:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/git_preflight.ps1
```

`scripts/git_preflight.ps1` は `git diff --check`、状態確認、差分表示、直近ログ表示、`dev_check` をまとめて実行します。trailing whitespace などの形式エラーは preflight で検出されます。

## ドキュメント

- [UHFリーダライタ開発者向け Quick Start](docs/uhf_reader_writer_programmer_quick_start.md)
- [アンテナ選択・順次Inventory確認メモ](docs/antenna_selection_and_inventory.md)
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
- 誤って送信出力を書き換えない。
- 送信出力値は `dBm * 10` を LSB/MSB の順で解析します。例: `F0 00` は `24.0 dBm` です。
- 実機確認時に `6144.0 dBm` のような異常値が出た場合は、送信出力値のエンディアン解釈を確認してください。
- 実機通信は、手順と接続条件を確認したうえで行う。
- `UHF_SET_INVENTORY_PARAM` は自動送信しない。
- Inventory結果は `inventory_results.txt`、`inventory_results.csv`、`inventory_results.json` に保存されます。
- CSVはExcelでの確認向け、JSONは後続処理やUTRRWManager結果との比較向けです。
- CSV/JSONには、取得できる場合は `antenna_number`、`antenna_label`、`antenna_description` も保存されます。
- Inventory読み取り前にブザー通知のON/OFFを選べます。ONの場合、タグありはピッピッピ、タグなしはピーで通知します。
- `q` で読み取りを終了しても、終了ブザーは鳴りません。
- NACK時は raw hex、エラー分類、現場向けの確認ポイントを表示します。詳細は [UHF Gen2 NACKエラー対応メモ](docs/nack_error_handling.md) を確認してください。

## UTR-SUN02-4CHのアンテナ確認

UTR-SUN02-4CHでは、アンテナ設定表示・接続チェックを実行すると、ANT0〜ANT3の接続状態を確認できます。

- ANT0: 内蔵アンテナ
- ANT1〜ANT3: 外付けアンテナ
- Inventory対象アンテナとして `0`、`1`、`0,1`、`all` を入力できます。
- 複数アンテナ選択時は、同時使用ではなく、ANT0→ANT1のように順番に切り替えてInventoryします。
- アンテナ切替時もFLASHは変更しません。コマンドモード用パラメータだけを一時変更し、終了時に元の設定へ復元します。
- 8CH機はアンテナ番号体系が異なるため、4CH用の処理をそのまま流用しないでください。

## セキュリティ・機密情報の注意

公開前に、以下の情報が含まれていないことを確認してください。

- 実IP
- 顧客名
- シリアル番号
- 未マスクの実測ログ
- 実測RSSI
- 実測PC/UII
- 認証情報、APIキー、トークン、パスワード

実機ログが必要な場合は、公開しても問題ないようにマスクした内容だけを使ってください。顧客情報、実IP、シリアル番号、未マスク実測ログはコミットしないでください。
Inventory結果ファイルに含まれる実測PC/UIIやログも、公開時は必ずマスクしてください。

## 今後の作業候補

- CSV/JSONのアンテナ情報を、実機確認結果に合わせて継続検証する。
- ANT別の読み取り枚数、平均RSSI、読み取り成功率を集計する。
- 8CH機の使用アンテナ番号読み取り/書き込みは、4CH機と体系が異なるため別PRで扱う。
- `src/utr_usb_sample.py` を新モジュール利用形に整理する。
- UTRRWManager側ログとPython側ログを比較する。
- 実機確認結果を踏まえて、サンプルとドキュメントを継続更新する。

## ライセンス

このリポジトリのソースコードは MIT License の下で公開されています。詳細は [LICENSE](./LICENSE) を確認してください。
