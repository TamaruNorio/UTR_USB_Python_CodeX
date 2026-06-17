#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""実機ログ・結果ファイル向けのマスク補助関数。

PC+UII / PC+EPC は実タグ固有情報を含むため、共有用ログやGit管理対象に
混入させない運用が必要です。このモジュールでは、実値を保持せずに、
同一実行内で同じタグを同じ仮名IDへ置き換える補助処理を提供します。
"""

from __future__ import annotations

MASKED_PC_UII_PREFIX = "MASKED_PC_UII_"


def build_masked_pc_uii_id(index: int) -> str:
    """1始まりの連番から、共有用の仮名PC+UIIを作成します。

    Args:
        index: 1以上の連番。

    Returns:
        例: `MASKED_PC_UII_001`

    Raises:
        ValueError: index が1未満の場合。
    """
    if index < 1:
        raise ValueError("index must be 1 or greater")
    return f"{MASKED_PC_UII_PREFIX}{index:03d}"


def get_or_create_masked_pc_uii_id(pc_uii_hex: str, mask_map: dict[str, str]) -> str:
    """実PC+UIIを、同一実行内だけで使う仮名IDへ置き換えます。

    実PC+UII自体は戻り値に含めません。すでに同じ実PC+UIIを見ている場合は、
    以前割り当てた仮名IDを返します。
    """
    if pc_uii_hex not in mask_map:
        mask_map[pc_uii_hex] = build_masked_pc_uii_id(len(mask_map) + 1)
    return mask_map[pc_uii_hex]
