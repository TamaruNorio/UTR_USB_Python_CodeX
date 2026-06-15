# Codex完全自動運用メモ

## 目的

Codexに修正、チェック、commit、push、PR作成、Actions確認、merge、ローカル同期まで任せる。

Codexから GitHub CLI `gh` を使い、PR作成とmergeまで自動化できることを確認する。

## 前提

- PowerShell 7 が利用可能
- Python / pytest が利用可能
- GitHub CLI `gh` が利用可能
- `gh auth status` で `TamaruNorio` としてログイン済み
- `repo` と `workflow` scope がある

## 基本フロー

1. `main` が clean であることを確認
2. 作業ブランチを作成
3. 必要な修正を実施
4. `git diff --check`
5. `.\scripts\dev_check.ps1`
6. `.\scripts\git_preflight.ps1`
7. commit
8. push
9. `gh pr create`
10. `gh pr checks --watch`
11. 成功時のみ `gh pr merge --merge --delete-branch`
12. `.\scripts\sync_after_merge.ps1 -Branch <作業ブランチ名>`

## 禁止事項

- mainへ直接commitしない
- mainへ直接pushしない
- checks失敗時にmergeしない
- conflictがある場合にmergeしない
- 実機通信しない
- `.codex/` をcommitしない
- APIキー、トークン、顧客情報、実IP、シリアル番号をcommitしない

## よく使う確認コマンド

- `gh --version`
- `gh auth status`
- `gh repo view TamaruNorio/UTR_USB_Python_CodeX`
- `git status --short`

## 備考

- 実機通信を伴う変更は、必ず別途明示承認を得る
- GitHub Actions warning や失敗が出た場合はmergeしない
- 作業後は `sync_after_merge` でmainへ戻す
