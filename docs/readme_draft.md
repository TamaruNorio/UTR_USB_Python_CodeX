# Takaya UTR-S201/202 USB Sample (Python)

## プロジェクト概要

このリポジトリは、TAKAYA製 RFID リーダライタ UTR-S201/202 シリーズを USBシリアル接続で扱う Python サンプルの作業用リポジトリです。

本サンプルは無保証で提供される確認用コードです。実際の運用環境で利用する場合は、機器設定、通信条件、プロトコル仕様、周辺環境を十分に確認してください。

## このリポジトリの位置づけ

`UTR_USB_Python_CodeX` は開発作業用リポジトリです。

公開用リポジトリは `UTR_USB_Python` です。この作業用リポジトリで整理・確認した内容を、レビュー後に公開用へ反映する想定です。

## 現在の状態

- USB実機通信はまだ未確認です。
- `src/utr_usb_sample.py` は元サンプルとして未変更です。
- 実機通信を伴わない純粋関数モジュールを追加済みです。
- pytest は `21 passed` の状態です。

追加済みの主な純粋関数モジュールは以下です。

- `src/utr_protocol.py`: フレーム、SUM、NACKなどのプロトコル補助処理。
- `src/utr_inventory.py`: RSSI変換、Inventory応答解析補助。
- `src/utr_commands.py`: コマンド定義、フレーム生成、ブザーコマンド生成。

## フォルダ構成

```text
UTR_USB_Python_CodeX/
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
| `src/utr_usb_sample.py` | USBシリアル接続用の元サンプル。現時点では未変更 |
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

## 実機確認前の注意

USB実機通信を行う前に、UTRRWManagerで事前確認してください。

- COMポートが認識されていることを確認する。
- UTR機器の電源を確認する。
- アンテナ接続を確認する。
- RFタグを準備する。
- ROMバージョンを確認する。
- 送信出力設定を確認する。
- 誤って送信出力を書き換えない。
- 実機通信は明示許可後のみ行う。

## セキュリティ・機密情報の注意

公開前に、以下の情報が含まれていないことを確認してください。

- 実IP
- 顧客名
- シリアル番号
- 実機ログ
- 実測RSSI
- 実測PC/UII
- 認証情報、APIキー、トークン、パスワード

実機ログが必要な場合は、公開用にマスクした内容だけを使ってください。

## 今後の作業候補

- README本体へこのドラフトを反映する。
- `src/utr_usb_sample.py` を新モジュール利用形に整理する。
- UTRRWManager側ログとPython側ログを比較する。
- 明示許可後にUSB実機通信を確認する。
- レビュー後、公開用 `UTR_USB_Python` に反映する。
