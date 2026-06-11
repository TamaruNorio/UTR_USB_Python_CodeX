# コミット前チェックリスト

コミット前に、以下を確認します。

## 開発チェック

- [ ] pytest が成功している
- [ ] `scripts/dev_check.ps1` が成功している
- [ ] `scripts/git_preflight.ps1` が成功している
- [ ] secret scan が成功している

## 変更範囲

- [ ] `src/utr_usb_sample.py` が未変更である
- [ ] USB実機通信を行っていない
- [ ] UTRRWManagerの実操作を行っていない
- [ ] `src.utr_usb_sample` を import していない
- [ ] `communicate()`、`main()`、`serial.Serial()` を呼んでいない

## 公開前の安全確認

- [ ] 機密情報が含まれていない
- [ ] 実IP、顧客名、シリアル番号が含まれていない
- [ ] 実機ログ、実測RSSI、実測PC/UIIを捏造していない
- [ ] README更新が必要かどうか確認した
- [ ] 公開前にREADMEとdocsの表現をレビューする

## 判断メモ

- READMEやdocsを更新する場合は、利用者向け説明を優先する。
- 公開前に、差分と説明内容を再確認する。
