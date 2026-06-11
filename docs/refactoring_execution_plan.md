# リファクタリング実行計画

この計画は、将来 `src/utr_usb_sample.py` を実際に整理するときの推奨手順です。今回は実装変更は行いません。

| Step | 目的 | 変更対象ファイル | 変更してはいけないこと | 確認コマンド | 想定される失敗 | 戻し方 |
|---:|---|---|---|---|---|---|
| 1 | 純粋関数だけを `utr_protocol.py` に抽出 | `src/utr_protocol.py`, `src/utr_usb_sample.py` | 実機通信処理を変更しない | `powershell -File scripts/dev_check.ps1` | import循環、定数参照漏れ | 抽出前の関数を戻す |
| 2 | テストのimport先を新モジュールに変更 | `tests/test_protocol_helpers.py` | テスト期待値を理由なく変えない | `powershell -File scripts/dev_check.ps1` | import先ミス、pyserial依存の混入 | テストimportを旧モジュールへ戻す |
| 3 | 既存 `src/utr_usb_sample.py` から新モジュールをimportする形に変更 | `src/utr_usb_sample.py` | CLI動作や通信順序を変えない | `powershell -File scripts/git_preflight.ps1` | 名前衝突、参照漏れ | import変更を戻す |
| 4 | Inventory解析系を `utr_inventory.py` に抽出 | `src/utr_inventory.py`, `src/utr_usb_sample.py`, `tests/` | `communicate()` を変更しない | `powershell -File scripts/dev_check.ps1` | RSSI/PC/UII解析の差分 | 関数移動を戻す |
| 5 | コマンド定義を `utr_commands.py` に抽出 | `src/utr_commands.py`, `src/utr_usb_sample.py` | 固定bytesを変更しない | `powershell -File scripts/dev_check.ps1` | コマンド名の参照漏れ | `COMMANDS` を元の場所へ戻す |
| 6 | `communicate` とCOMポート選択を `utr_usb_transport.py` に抽出 | `src/utr_usb_transport.py`, `src/utr_usb_sample.py` | タイムアウト、送受信順序を変えない | `powershell -File scripts/git_preflight.ps1` | 実機なしでは検出できない通信差分 | 抽出前の `communicate` に戻す |
| 7 | `main` とCLI処理を `utr_cli.py` に整理 | `src/utr_cli.py`, `src/utr_usb_sample.py` | 入力プロンプトや実行順序を不用意に変えない | `powershell -File scripts/dev_check.ps1` | ユーザー入力フローの破損 | `main` を旧構成へ戻す |
| 8 | `src/utr_usb_sample.py` を互換エントリーポイントとして残す | `src/utr_usb_sample.py` | ファイル削除、互換性破壊 | `powershell -File scripts/git_preflight.ps1` | 既存実行方法が壊れる | 旧エントリーポイントを復元 |
| 9 | 実機通信前にpytest/dev_check/git_preflightを実行 | 変更なし | 実機通信を始めない | `powershell -File scripts/dev_check.ps1`, `powershell -File scripts/git_preflight.ps1` | テスト失敗、secret scan失敗 | 直前の変更を見直す |
| 10 | USB実機通信確認 | 実機確認ログ | 手順確認なしで実機通信しない、送信出力を書き換えない | 実機確認手順に従う | COMポート不一致、NACK、タイムアウト | 実機操作を止め、ログを保存して原因確認 |

## 実行時の共通ルール

- 各Stepは小さく分け、Stepごとに pytest/dev_check を通します。
- 実機通信を伴う処理変更は、手順と接続条件を確認してから扱います。
- 送信出力設定、タグ書き込み、ブザー制御は副作用があるため慎重に扱います。
- 不明な仕様は「要仕様書確認」として残し、推測で実装を変えません。
- 戻す場合は、対象Stepで変更したファイルだけを戻す方針にします。
