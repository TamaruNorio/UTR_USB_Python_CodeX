# USB接続 Inventory実機確認手順

## 目的

この手順書は、USB接続のUTR RFIDリーダライタで、`tools/usb_inventory_batch.py` による読み取り処理とCSV保存を確認するための手順です。

この確認では、実機への永続設定変更は行いません。Inventoryの連続実行、RSSI集計、タグ別読み取り回数集計、CSV通常行、CSV末尾SUMMARY行を確認します。

## 前提条件

- Windows環境で作業する。
- PowerShellを使用する。
- Pythonを使用できる。
- USB仮想COMポートでUTR RFIDリーダライタへ接続できる。
- COMポート番号とボーレートが分かっている。
- この手順では例として `COM6` / `115200bps` を使用する。
- 実運用では、COMポート番号を現場PC環境に合わせて変更する。

## 安全方針

- `UHF_SET_INVENTORY_PARAM` は自動送信しない。
- FLASH書き込みは行わない。
- 送信出力変更は行わない。
- 周波数変更は行わない。
- 8CHアンテナ切替は行わない。
- 実機への永続設定変更は行わない。

## 作業前確認

PowerShellで以下を実行します。

```powershell
git switch main
git pull
git status --short
py -m pytest
```

期待結果:

- `git status --short` が空である。
- `py -m pytest` が `234 passed` で完了する。

## USB Inventory batch runner の確認

実機のCOMポートとボーレートを指定して、Inventoryを10回実行します。

```powershell
py tools/usb_inventory_batch.py --port COM6 --baudrate 115200 --repeat 10 --interval 0.1
```

確認する内容:

- 接続成功が表示される。
- ROMバージョン取得が成功する。
- コマンドモード切替が成功する。
- `UHF_GET_INVENTORY_PARAM` が実行される。
- `UHF_SET_INVENTORY_PARAM` が自動送信されない。
- Inventory結果が表示される。
- CSVが `logs/usb_sample` に保存される。
- Inventory回数が10回である。
- タグ応答数が表示される。
- RSSI最小値、最大値、平均値が表示される。
- タグ別読み取り回数が表示される。
- SUMMARY行がCSV末尾に出力される。

## CSV確認方法

最新のCSVファイルを確認します。

```powershell
Get-ChildItem .\logs\usb_sample\inventory_batch_*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content .\logs\usb_sample\inventory_batch_YYYYMMDD_HHMMSS.csv | Select-Object -Last 12
```

2行目の `inventory_batch_YYYYMMDD_HHMMSS.csv` は、1行目で確認した最新CSV名に置き換えてください。

CSV末尾に、通常行に続いて以下のようなSUMMARY行が出力されていることを確認します。

```text
SUMMARY,total_iterations,10
SUMMARY,total_read_time_sec,...
SUMMARY,total_tag_responses,...
SUMMARY,unique_tags,...
SUMMARY,average_tag_count,...
SUMMARY,min_rssi,...
SUMMARY,max_rssi,...
SUMMARY,average_rssi,...
```

## よくあるエラーと対処

### COMポートが開けない

- COMポート番号を確認する。
- デバイスマネージャーでUSB仮想COMポートを確認する。
- UTRRWManagerなど、他ソフトが接続中でないか確認する。
- USBケーブルを確認する。
- USBシリアルドライバを確認する。

### 通信できない

- ボーレートを確認する。
- リーダライタの電源を確認する。
- USBケーブルを抜き差しする。
- PCを再起動する。

### タグが読めない

- タグ位置を確認する。
- アンテナ位置を確認する。
- 対応タグであることを確認する。
- 金属や水分の影響を確認する。

### CSVが見つからない

- `logs/usb_sample` を確認する。
- `--csv` 指定時は指定先を確認する。

### pytestが失敗する

- 仮想環境が有効か確認する。
- `requirements-dev.txt` を再インストールする。
- 変更差分を確認する。

## 実機確認結果の記録テンプレート

| 項目 | 記録 |
|---|---|
| 確認日 |  |
| 確認者 |  |
| リーダライタ機種 |  |
| ROMバージョン |  |
| 接続方式 | USBシリアル |
| COMポート |  |
| ボーレート |  |
| 実行コマンド |  |
| Inventory回数 |  |
| 読み取りタグ数 |  |
| RSSI最小値 |  |
| RSSI最大値 |  |
| RSSI平均値 |  |
| CSVファイル名 |  |
| 備考 |  |
