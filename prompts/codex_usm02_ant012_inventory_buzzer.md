# Codex依頼文: USM02 ANT0〜2 Inventory・タグ検出時ブザー確認

`UTR_USB_Python_CodeX` の `feature/usm02-v117-validation-harness` ブランチで、コードを変更せず、ANT0・ANT1・ANT2のInventoryとタグ検出時ブザーだけを実行してください。

前提実機:

- UTR-SUN02-4CH / USM02 Ver.2.052
- COM6 / 115200 bps
- ANT0、ANT1、ANT2にタグを1枚ずつ配置済み
- ブザー音は「ピッピッピ」を使用

禁止:

- Kill、Lock、UHF_Encode、FLASH設定初期化を送信しない
- FLASH、タグメモリ、Access Passwordを書き換えない
- 指定CLI以外から実機コマンドを追加送信しない
- 生Hex、PC/UII/EPC/TID、タグ固有値、製造番号、パスワードを回答へ載せない
- コード変更、commit、push、PR変更、mergeをしない

手順:

```powershell
cd C:\Users\tamaru\Documents\Codex\repos\UTR_USB_Python_CodeX
git fetch origin
git switch feature/usm02-v117-validation-harness
git pull --ff-only
git status --short
$env:PYTHONPATH = "."
py -m pytest -q
py -m src.utr_usm02_inventory_buzzer_cli --antennas 0,1,2
py -m src.utr_usm02_inventory_buzzer_cli --execute --port COM6 --baudrate 115200 --antennas 0,1,2 --json-out runtime_logs\usm02_ant012_inventory_buzzer.json
git status --short
```

実行時の判断:

- bootstrapでANT0、ANT1、ANT2のいずれかが接続OKでなければ、Inventoryを実行せず停止する。
- アンテナID出力がONでなければ停止する。
- EPCバッファリングがOFFでなければ停止する。
- NACK、timeout、タグ応答ANT不一致、読戻し不一致、復元失敗が出たら、追加コマンドを送らず停止する。
- タグ0件のANTは異常と決めつけず、ブザー未送信として記録する。
- プログラムのブザーACKと、人が実際に音を聞いた確認を混同しない。

回答項目:

1. pytest結果
2. dry-run結果
3. ROM、機種、接続OKアンテナ、アンテナID出力
4. ANT0、ANT1、ANT2ごとのタグ応答数とユニークタグ数
5. ANT0、ANT1、ANT2ごとの完了ACK枚数と実使用CH
6. ANT0、ANT1、ANT2ごとのブザー送信有無とブザーACK
7. ユーザーに、ANT0、ANT1、ANT2の「ピッピッピ」音が実際に聞こえたか確認する
8. 開始前アンテナ設定と復元結果
9. RF送信はInventory最大3回、FLASH変更なし、タグ書込なし
10. NACK、timeout、例外、復元失敗の有無
11. `git status --short`
