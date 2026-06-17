# UTR-SUN02 8CH機 読み取り専用アンテナ診断

## 目的

UTR-SUN02V-8CH / UTR-SUN02-8CH の実機で、ANT1〜ANT8の接続状態を読み取り専用で確認します。

## 実行コマンド

```powershell
cd "D:\My documents\Python Scripts\CodeX\UTR_USB_Python_CodeX"
py .\src\utr_8ch_antenna_diagnostics_cli.py
```

## この診断で行うこと

- USBシリアル接続
- ROMバージョン読み取り
- 8CH機種判定
- コマンドモード切替
- ANT1〜ANT8 の UHF_CheckAntenna

## この診断で行わないこと

- アンテナ切替設定の書き込み
- 送信出力変更
- Inventory
- FLASH書き込み
- UHF_SET_INVENTORY_PARAM送信

## 期待する表示

```text
ROMシリーズ名: USM08
仕様書照合機種: UTR-SUN02-8CH（外付け8CH）

=== 8CHアンテナ診断（読み取り専用） ===
8CH機種: UTR-SUN02-8CH（外付け8CH）
UHF_CheckAntennaでは 00h〜07h が ANT1〜ANT8 に対応します。
使用アンテナ番号系では ANT1=00h, ANT2=20h, ..., ANT8=E0h として扱います。
本診断では接続確認だけを行い、アンテナ切替設定やFLASHは変更しません。

アンテナ接続チェックを開始します。
対象機種: UTR-SUN02-8CH（外付け8CH）
ANT1 接続確認中... 外付けアンテナ
  ANT1（外付けアンテナ）: 接続OK
...
ANT8 接続確認中... 外付けアンテナ
  ANT8（外付けアンテナ）: 接続OK

=== 8CH診断結果まとめ ===
接続OKアンテナ: ANT1, ANT2, ...
接続を閉じました。
```

## 次の段階

この診断結果で接続OKだったアンテナをもとに、8CH用のInventory切替処理を追加します。

UTR-SUN02-8CHでは、使用アンテナ番号系は以下の対応になります。

| 物理ポート | 使用アンテナ番号系 |
|---|---:|
| ANT1 | 00h |
| ANT2 | 20h |
| ANT3 | 40h |
| ANT4 | 60h |
| ANT5 | 80h |
| ANT6 | A0h |
| ANT7 | C0h |
| ANT8 | E0h |
