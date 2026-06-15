# USB実機確認メモ

## 対象

UTR-S201/202系 USBシリアル接続サンプル。

## 確認環境

- COMポート: COM6
- 通信速度: 115200 bps
- OS: Windows環境

## 確認できたこと

- ROM_VERSION_CHECK: ROMバージョン応答を確認
- COMMAND_MODE_SET: ACK応答を確認
- UHF_GET_INVENTORY_PARAM: 応答を確認
- UHF_INVENTORY: タグ応答と読み取り完了ACKを確認
- 読み取り枚数: 1
- 読み取りチャンネル: 5
- UHF_BUZZER_pipipi: ACK応答と実音を確認

## UHF_GET_INVENTORY_PARAM 応答例

```text
02 00 30 0B 41 00 1F DC 81 02 00 00 00 00 02 03 01 0D
```

## 注意

- 実機ログは機器設定、タグ、環境により変わる。
- 顧客情報、実IP、シリアル番号、未マスクの実測ログはコミットしない。
- 送信出力や設定変更系コマンドは不用意に実行しない。
- `UHF_SET_INVENTORY_PARAM` は自動送信しない。
