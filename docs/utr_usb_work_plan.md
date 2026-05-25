# UTR USB版 作業計画

## このリポジトリの目的

`UTR_USB_Python_CodeX` は、USBシリアル接続版の Python サンプルを安全に確認・整理するための作業用リポジトリです。

公開用リポジトリは `UTR_USB_Python` です。このリポジトリで確認した内容を、そのまま無条件に公開用へ反映するわけではありません。

## 現時点の方針

- `src/utr_usb_sample.py` は、現時点では変更しません。
- USB実機通信は、明示許可がある場合だけ行います。
- `git commit`、`git push`、PR作成、merge は、明示許可がある場合だけ行います。
- Phase 1 では、通信処理の変更ではなく、資料整理と確認手順の準備を行います。

## 今後の作業段階

| Phase | 作業内容 | 目的 |
|---|---|---|
| Phase 1 | USB版資料整理 | 作業方針、比較観点、実機確認前チェックを文書化する |
| Phase 2 | 実機確認前チェック | Python環境、COMポート、機器状態を確認する |
| Phase 3 | UTRRWManager比較 | Pythonサンプルの動作と UTRRWManager の動作を比較する |
| Phase 4 | src整理方針の設計 | `src/utr_usb_sample.py` をどう整理するか検討する |
| Phase 5 | 最小リファクタリング | 動作を変えずに、必要最小限の整理を行う |
| Phase 6 | USB実機通信確認 | 明示許可後に実機で通信確認を行う |
| Phase 7 | 公開用反映 | 確認済み内容を `UTR_USB_Python` へ反映する |

## 注意事項

USB版は LAN版とは異なり、TCP/IP ではなく pyserial と COMポートを使います。通信確認時は、Python側ログと UTRRWManager側ログを見比べながら進めます。
