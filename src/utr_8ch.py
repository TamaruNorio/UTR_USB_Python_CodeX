#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR-SUN02 8CH機向けの補助関数。

このモジュールは、8CH機の機種判定と表示文言だけを扱います。
実機通信、アンテナ切替、設定書き込みは行いません。
"""

from __future__ import annotations

EIGHT_CH_MODEL_KEYS = frozenset({"UTR-SUN02V-8CH", "UTR-SUN02-8CH"})


def is_8ch_model_key(model_key: str | None) -> bool:
    """仕様書照合機種キーが8CH機か判定します。"""
    return model_key in EIGHT_CH_MODEL_KEYS


def format_8ch_diagnostic_notes(model_key: str | None) -> list[str]:
    """8CH診断時に表示する注意点を返します。"""
    if model_key == "UTR-SUN02-8CH":
        return [
            "8CH機種: UTR-SUN02-8CH（外付け8CH）",
            "UHF_CheckAntennaでは 00h〜07h が ANT1〜ANT8 に対応します。",
            "使用アンテナ番号系では ANT1=00h, ANT2=20h, ..., ANT8=E0h として扱います。",
            "本診断では接続確認だけを行い、アンテナ切替設定やFLASHは変更しません。",
        ]
    if model_key == "UTR-SUN02V-8CH":
        return [
            "8CH機種: UTR-SUN02V-8CH（外部アンテナユニット対応8CH）",
            "UHF_CheckAntennaでは 00h〜07h が ANT1〜ANT8 に対応します。",
            "使用アンテナ番号系では 内部アンテナ番号×32+外部アンテナ番号 の体系を使います。",
            "本診断では接続確認だけを行い、アンテナ切替設定やFLASHは変更しません。",
        ]
    return [
        "8CH機ではないため、8CH専用診断は実行しません。",
    ]
