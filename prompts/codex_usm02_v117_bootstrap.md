# Codex依頼文: USM02事前確認だけを実行

対象リポジトリで、既存コードを変更せず、以下だけを実行してください。

対象:

- UTR-SUN02-4CH / ROMシリーズUSM02
- USB COM6
- 115200 bps

禁止:

- Kill、Lock、UHF_Encode、FLASH設定初期化を送信しない
- タグメモリを書き換えない
- FLASHを書き換えない
- PC/UII/EPC/TID、シリアル番号、パスワードの実値を回答やGitへ載せない
- merge、commit、push、PR作成をしない

手順:

```powershell
cd C:\Users\tamaru\Documents\Codex\repos\UTR_USB_Python_CodeX
git status --short
git branch --show-current
$env:PYTHONPATH = "."
$env:UV_CACHE_DIR = "$env:TEMP\uv-cache"
uv run --with pytest --with "pyserial>=3.5" pytest -q
py -m src.utr_usm02_v117_validation_cli --rom-number 2052
py -m src.utr_usm02_v117_validation_cli --execute-bootstrap --port COM6 --baudrate 115200 --json-out runtime_logs\usm02_v117_bootstrap.json
git status --short
```

予期しないNACK、timeout、対象機種不一致、例外が1件でも出たら、その時点で停止してください。

回答は次の項目だけにしてください。

1. pytest結果
2. dry-runの54件集計
3. 実機ROM（シリーズ名USM02とバージョンだけ。製造番号は記載しない）
4. 物理アンテナ容量
5. 設定アンテナ番号
6. 接続OKアンテナ番号
7. アンテナID出力、TID付加、EPCバッファリング、読取サイクル完了応答、アンテナ切替完了応答、キャリア検知応答のON/OFF
8. NACK、timeout、例外の有無
9. `git status --short`（`runtime_logs/`以外の変更がないこと）

生の送受信Hexとタグ固有値は回答へ貼らないでください。
