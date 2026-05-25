## TAKAYA RFID リーダライタ サンプルプログラム ドキュメント

> **ドキュメントの全体像や他のサンプルプログラムについては、[こちらのランディングページ](https://tamarunorio.github.io/TAKAYA-RFID-Sample-Code/)をご覧ください。**

# Takaya UTR-S201/202 USB Sample (Python)

タカヤ製RFIDリーダライタ **UTR-S201/202 シリーズ** を USBシリアル接続で制御するための **Pythonサンプルプログラム** です。本プログラムは社内検証用に作成したものを公開しており、**無保証** での提供となります。

## 概要

このサンプルプログラムは、UTR-S201/202シリーズリーダライタをUSBシリアル接続で制御するためのPythonサンプルです。基本的なタグ読み取り機能を提供し、コンソールにタグ読取結果を表示します。

## 動作環境

-   OS: Windows 10 / 11
-   Python: 3.8 以上
-   必要ライブラリ: [pyserial](https://pypi.org/project/pyserial/)

## セットアップと実行方法

1.  **リポジトリのクローン**:
    ```bash
    git clone https://github.com/TamaruNorio/UTR_USB_Python.git
    cd UTR_USB_Python
    ```
2.  **必要ライブラリのインストール**:
    ```bash
    pip install pyserial
    ```
3.  **UTR-S201/202 リーダライタをUSB接続**:
4.  **実行**:
    ```bash
    python src/utr_usb_sample.py
    ```
    コンソールにタグ読取結果が表示されます。

## プロジェクト構成

```
UTR_USB_Python/
├─ src/
│  └─ utr_usb_sample.py   # メインスクリプト
├─ .gitignore
└─ README.md
```

## ライセンス

このリポジトリのソースコードは **MIT License** の下で公開されています。詳細は [LICENSE](./LICENSE) ファイルをご確認ください。


## Development checks

This CodeX work repository includes small PowerShell helpers for local checks and PR preparation.

```powershell
.\scripts\dev_check.ps1
.\scripts\git_preflight.ps1
.\scripts\publish_pr.ps1 -Message "commit message" -Title "PR title"
.\scripts\sync_after_merge.ps1 -Branch "work-branch"
```

- `dev_check.ps1` shows `git status --short`, runs pytest against `tests`, runs the blocked-text scan, and checks `.gitignore`.
- `git_preflight.ps1` shows branch, status, diff stat, recent log, and then runs `dev_check.ps1`.
- `publish_pr.ps1` commits and pushes only after `YES` confirmation, generates `pr_body.md`, copies it to the clipboard, and opens the PR creation URL when it can infer one.
- `sync_after_merge.ps1` syncs `main` and deletes the local work branch only after `YES` confirmation.

These helpers do not run USB hardware communication and do not run `src/utr_usb_sample.py`.
