# Codex依頼文: USM02 Phase 2安全制御確認

`UTR_USB_Python_CodeX` の `feature/usm02-v117-validation-harness` ブランチで、コードを変更せずPhase 2だけを実行してください。

前提実機:

- UTR-SUN02-4CH / USM02 Ver.2.052
- COM6 / 115200 bps
- 設定アンテナ: ANT0
- 接続OK: ANT0、ANT1
- bootstrapでNACK、timeout、例外なし

禁止:

- Kill、Lock、UHF_Encode、FLASH設定初期化を送信しない
- FLASH、タグメモリ、Access Passwordを書き換えない
- RF送信はPhase 2 CLI内のInventory 1回だけに限定する
- 生Hex、タグ固有値、製造番号、パスワードを回答へ載せない
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
py -m src.utr_usm02_safe_controls_cli --target-antenna 1 --verify-rf-channel
py -m src.utr_usm02_safe_controls_cli --execute --port COM6 --baudrate 115200 --target-antenna 1 --verify-rf-channel --json-out runtime_logs\usm02_phase2_safe_controls.json
git status --short
```

NACK、timeout、読戻し不一致、復元失敗、対象条件不一致が出たら、追加コマンドを送らず停止してください。

回答項目:

1. pytest結果
2. dry-run結果
3. ブザーACKの成否（音が聞こえたかは推測せず、ユーザー確認事項として分ける）
4. アンテナの変更前→一時変更→復元と、各読戻し結果
5. 開始CHの変更前→一時変更→復元
6. 使用許可CHが変更されていないこと
7. Inventoryのタグ応答数、タグ応答ANT、完了ACKの実使用CH（タグ固有値は記載しない）
8. RF送信はInventory 1回だけ、FLASH変更なし、タグ書込なし
9. NACK、timeout、例外、復元失敗の有無
10. `git status --short`
