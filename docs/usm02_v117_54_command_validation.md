# USM02 Ver.1.17 54コマンド検証

## 目的

UTR-SUN02-4CH / ROMシリーズUSM02について、通信プロトコル説明書Ver.1.17の通常コマンド54件を、漏れと重複なく検証するための入口です。

54件を一律に「ACK確認」とは扱いません。正常時の応答形態、機種・ROM対応、安全条件により、次を区別します。

- 単一ACK
- 設定によりACKまたは無応答
- タグ応答0件以上＋完了ACK
- 仕様上の無応答
- NACK（解析済みでも正常完了にはしない）
- USM02では非対応
- 実機ROMでは非対応
- 条件未準備
- ユーザー判断で非実行

## 対象実機

- 機種: UTR-SUN02-4CH
- ROMシリーズ: USM02
- 接続: USBシリアル
- 既定ポート: COM6
- 既定速度: 115200 bps

## 1. 実機に接続しないdry-run

PowerShellでリポジトリ直下から実行します。

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_v117_validation_cli --rom-number 2052
```

`2052`はVer.2.052を仮定する指定です。実機値ではありません。実ROMが不明な場合は `--rom-number` を省略してください。

dry-runではCOMポートを開かず、54件の計画と集計だけを表示します。

## 2. 実機の事前情報だけを取得

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_v117_validation_cli `
  --execute-bootstrap `
  --port COM6 `
  --baudrate 115200 `
  --json-out runtime_logs\usm02_v117_bootstrap.json
```

この段階で送信するのは、次の事前確認だけです。

1. ROMバージョンを読み、USM02 / UTR-SUN02-4CHを確定する。
2. RAM上の動作モードをコマンドモードへ切り替える。
3. コマンドモードのアンテナ切替設定を読む。
4. ANT0〜ANT3へUHF_CheckAntennaを送り、物理接続状態を確認する。
5. Inventoryパラメータを読み、TID付加設定を確認する。
6. コマンドモードと自動読み取りモードのEPC(UII)関連設定を読み、応答件数・順序へ影響する設定を確認する。

次の3種類のアンテナ数は別々に記録します。

| 項目 | 取得元 | 意味 |
|---|---|---|
| 物理容量 | ROMシリーズから確定した機種仕様 | USM02ではANT0〜ANT3の4ポート |
| 設定アンテナ | 7.4.5 アンテナ切替設定 | 現在「使用する」と設定されたアンテナ |
| 接続OKアンテナ | 7.3.5 UHF_CheckAntenna | 実際に接続OKと応答したアンテナ |

## 3. 2バイト目の解釈

応答の2バイト目は、常にアンテナ番号ではありません。

- RFタグデータ応答（コマンド `6Ch`）かつ「アンテナID出力=有効」の場合だけ、アンテナ番号として解釈します。
- 通常ACK、NACK、完了ACK、または「アンテナID出力=無効」のRFタグ応答では、リーダライタIDとして解釈します。

## 4. 強制安全ルール

- Kill、Lock、UHF_Encode、FLASH設定初期化は送信しません。
- 予期しないNACK、timeout、復元失敗が発生したら後続送信を止めます。
- Access/Kill Passwordをログへ出しません。
- PC/UII/EPC/TIDの実値を共有用ログへ出しません。
- 設定変更は事前読取、同値書込、再読取、復元確認の順で行います。
- タグ書込は廃棄可能タグのUser領域だけを対象とし、事前読取と復元を必須とします。
- UHF_ThroughCmdは、TIDでタグICを特定し、そのIC向け安全コマンドを確定できるまで実行しません。

## 5. 現在の実装範囲

現時点のCLIは、54件の仕様カタログ、応答検証ロジック、dry-run、実機事前確認までを実装しています。54件すべてを自動送信する機能ではありません。

まず実機事前確認結果からROMと設定依存条件を確定し、その結果に基づいて実行可能なコマンドだけを次の実装単位へ進めます。これにより、非対応コマンドや破壊的コマンドを「54件達成」のために誤送信することを防ぎます。

## 6. Phase 2: 安全制御確認

bootstrapが正常で、USM02、接続ANT、設定値を確認できた場合だけ実行します。

dry-run:

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_safe_controls_cli --target-antenna 1
```

実機実行:

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_safe_controls_cli `
  --execute `
  --port COM6 `
  --baudrate 115200 `
  --target-antenna 1 `
  --verify-rf-channel `
  --json-out runtime_logs\usm02_phase2_safe_controls.json
```

実行内容:

1. ROM、応答依存設定、ANT0〜ANT3の接続状態を再取得する。
2. ブザー制御を応答要求ありで1回実行し、ACKを確認する。
3. コマンドモードRAMのアンテナを接続OKのANT1へ一時変更する。
4. アンテナ設定を読み戻す。
5. コマンドモードRAMの周波数開始CHを、現在使用許可されている26〜32ch内の別CHへ一時変更する。
6. 周波数設定を読み戻し、使用許可CHマスクが不変であることを確認する。
7. Inventoryを1回だけ実行し、タグ固有値を保存せず、タグ応答ANTと完了ACKの実使用CHを確認する。
8. 周波数開始CHを元へ戻して読み戻す。
9. アンテナ設定を元へ戻して読み戻す。

周波数確認で変更するのはRAM上の「開始チャンネル番号」だけです。使用許可CHは変更せず、FLASHへ保存しません。`--verify-rf-channel` を指定した場合だけInventoryを1回実行します。タグのPC/UII/EPC/TIDは表示・保存せず、応答件数、アンテナ番号、完了ACKの実使用CHだけを残します。「現在設定されているチャンネル番号」は最後にキャリア出力したCHなので、Inventory前の読戻し時点では変化していなくても正常です。

例外、NACK、読戻し不一致の場合も `finally` で周波数、アンテナの順に復元します。復元確認に失敗した場合は後続操作を行わず、UTRRWManagerまたは読取コマンドで現在値を確認してください。

## 7. ANT0〜2 Inventory・タグ検出時ブザー確認

ANT0、ANT1、ANT2へタグを1枚ずつ置いた状態で、アンテナ別の読取と条件付きブザーを確認します。これは54コマンド全件検証とは分けた、限定的な実機確認です。

dry-run:

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_inventory_buzzer_cli --antennas 0,1,2
```

実機実行:

```powershell
$env:PYTHONPATH = "."
py -m src.utr_usm02_inventory_buzzer_cli `
  --execute `
  --port COM6 `
  --baudrate 115200 `
  --antennas 0,1,2 `
  --json-out runtime_logs\usm02_ant012_inventory_buzzer.json
```

実行順序:

1. ROM、応答依存設定、ANT0〜ANT3の物理接続を再取得する。
2. アンテナID出力がON、EPCバッファリングがOFF、ANT0〜2がすべて接続OKであることを確認する。
3. 開始前のコマンドモードRAMアンテナ設定を読み取る。
4. ANT0、ANT1、ANT2の順にRAM設定を切り替え、毎回読み戻す。
5. 各ANTでInventoryを1回だけ実行する。
6. タグ応答が1件以上のANTだけ、応答要求ありの「ピッピッピ」ブザーを1回送信しACKを確認する。
7. 開始前のアンテナ設定へ戻し、読み戻す。

画面とJSONへ残すのは、ANT別のタグ応答数、ユニークタグ数、完了ACK枚数、実使用CH、ブザーACK、復元結果だけです。PC/UII/EPC/TID、生フレームは残しません。タグが0件のANTではブザーを送信しません。NACK、timeout、応答不正、ANT番号不一致が出た場合は後続ANTへ進まず、`finally` で開始前のアンテナ設定へ復元します。

ブザーACKはリーダライタがコマンドを正常受理した確認です。実際に音が聞こえたかは自動判定できないため、ANT0、ANT1、ANT2ごとに人が確認し、ACK結果とは分けて記録します。

## 8. 開発者確認

```powershell
$env:PYTHONPATH = "."
py -m pytest -q
py -m compileall -q src tests
git diff --check
```

実機結果のJSONは `runtime_logs/` に保存し、Gitへコミットしません。
