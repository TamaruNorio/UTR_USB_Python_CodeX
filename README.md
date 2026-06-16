# Takaya UTR-S201/202 USB Sample (Python)

## プロジェクト概要

このリポジトリは、TAKAYA製 RFID リーダライタ UTR-S201/202 シリーズを USBシリアル接続で扱う Python サンプルです。

本サンプルは無保証で提供される確認用コードです。実際の運用環境で利用する場合は、機器設定、通信条件、プロトコル仕様、周辺環境を十分に確認してください。

## このリポジトリの位置づけ

このリポジトリでは、USBシリアル接続サンプルをベースに、実機通信を伴わずに確認できるプロトコル処理、Inventory解析、コマンド生成処理を分離しています。

## 現在の状態

- USB実機で ROM_VERSION_CHECK、COMMAND_MODE_SET、UHF_GET_INVENTORY_PARAM、UHF_INVENTORY、UHF_BUZZER_pipipi の応答を確認済みです。
- Inventory応答解析では、タグデータレスポンス、読み取り完了ACK、NACKを扱う補助処理を追加済みです。
- ブザーコマンドは ACK 応答と実音を確認済みです。
- 実機通信を伴わない純粋関数モジュールを追加済みです。
- pytest は `26 passed` の状態です。
- PowerShell 7 環境で、Codex Actions、`scripts/dev_check.ps1`、`scripts/git_preflight.ps1` による確認運用を整備済みです。

追加済みの主な純粋関数モジュールは以下です。

- `src/utr_protocol.py`: フレーム、SUM、NACKなどのプロトコル補助処理。
- `src/utr_inventory.py`: RSSI変換、Inventory応答解析補助。
- `src/utr_commands.py`: コマンド定義、フレーム生成、ブザーコマンド生成。

## フォルダ構成

```text
UTR_USB_Python/
├─ src/
│  ├─ utr_usb_sample.py
│  ├─ utr_protocol.py
│  ├─ utr_inventory.py
│  └─ utr_commands.py
├─ tests/
│  ├─ test_smoke.py
│  ├─ test_protocol_helpers.py
│  └─ test_commands.py
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
| `tests/test_protocol_helpers.py` | プロトコル/Inventory補助関数のpytest |
| `tests/test_commands.py` | コマンド定義/生成関数のpytest |
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

- [フィールドサポート向け Quick Start](docs/quick_start_for_field_support.md)
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
- Inventory読み取り前にブザー通知のON/OFFを選べます。ONの場合、タグありはピッピッピ、タグなしはピーで通知します。
- `q` で読み取りを終了しても、終了ブザーは鳴りません。
- NACK時は raw hex、エラー分類、現場向けの確認ポイントを表示します。詳細は [UHF Gen2 NACKエラー対応メモ](docs/nack_error_handling.md) を確認してください。

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

- `src/utr_usb_sample.py` を新モジュール利用形に整理する。
- UTRRWManager側ログとPython側ログを比較する。
- 実機確認結果を踏まえて、サンプルとドキュメントを継続更新する。

## ライセンス

このリポジトリのソースコードは MIT License の下で公開されています。詳細は [LICENSE](./LICENSE) を確認してください。
