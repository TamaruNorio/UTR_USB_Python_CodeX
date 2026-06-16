# 現在の作業状況

## 基準コミット

```text
d41585e Drain serial input before antenna restore
```

## 実機確認済みの主な範囲

- USBシリアル接続での実機確認を継続しています。
- 主な確認構成は、UTR-SUN02-4CH、COM6、115200bps、ROMバージョン `2052USM02` です。
- UTR-SUN02-4CHでは、ANT0〜ANT3の接続確認、コマンドモード用アンテナ設定の一時変更、順次Inventory、終了時復元を確認済みです。
- Ctrl+C中断時は、復元前に受信バッファをクリアし、遅れて流れてくるInventory応答を読み捨ててから、元のコマンドモード用アンテナ設定へ復元する処理を追加済みです。
- 実機確認では、ANT1からAnt0への復元成功を確認済みです。

## 現在の設計方針

- FLASHは変更しません。
- コマンドモード用アンテナ設定だけを一時変更します。
- 終了時・中断時は、可能な限り元のアンテナ設定へ戻します。
- `UHF_SET_INVENTORY_PARAM` は自動送信しません。
- 8CH機のアンテナ制御は、4CH処理と混同しません。
- 実タグIDを含む `PC+UII` / `PC+EPC` は、公開ドキュメント、Issue、PR本文、共有ログに含めません。

## 結果保存の現状

- Inventory結果は、TXT/CSV/JSONに保存します。
- CSV/JSONには、取得できる場合、以下のアンテナ情報も保存します。

```text
antenna_number
antenna_label
antenna_description
```

- Inventoryを1回以上実行した場合は、タグ0枚でも保存します。
- Inventory自体を実行していない場合は保存しません。
- 既存CSVのヘッダーが旧形式の場合は、`inventory_results_legacy_YYYYMMDD_HHMMSS.csv` に退避してから現行ヘッダーで保存します。
- `inventory_results.txt`、`inventory_results.csv`、`inventory_results.json`、`inventory_results_legacy_*.csv` はGit管理対象外です。

## 直近確認結果

```text
python -m pytest
110 passed
```

## 次の作業候補

| 優先 | 内容 | 方針 |
|---|---|---|
| 1 | README / Quick Start追従 | 現状の実装、実機確認範囲、未対応範囲を明記する |
| 2 | 復元ACK探索の堅牢化 | 現在の実機安定点を壊さないよう、別PRで小さく実装する |
| 3 | 日時付き結果ファイル名 | 既存の追記運用と比較し、要件を明確化してから実装する |
| 4 | タグIDマスク表示オプション | 公開ログ安全性向上のため、開発者向けオプションとして検討する |
| 5 | 8CH機対応 | UTR-SUN02V-8CH / UTR-SUN02-8CH の仕様と実機ログを確認して別設計にする |
