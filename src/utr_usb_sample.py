#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USB sample default entry point.

既存の関数・定数は `utr_usb_sample_legacy.py` から再公開します。
通常実行時は、送信出力一時変更つきInventoryフローを起動します。

この構成により、既存テストや他モジュールからの import 互換性を維持しながら、
標準入口 `py .\src\utr_usb_sample.py` を新しいInventoryフローへ切り替えます。
"""

from __future__ import annotations

try:
    from src.utr_usb_sample_legacy import *  # noqa: F401,F403
except ModuleNotFoundError:
    from utr_usb_sample_legacy import *  # noqa: F401,F403


def main() -> None:
    """送信出力一時変更つきInventoryフローを起動します。"""
    try:
        from src.utr_usb_inventory_with_output_power import main as integrated_main
    except ModuleNotFoundError:
        from utr_usb_inventory_with_output_power import main as integrated_main

    integrated_main()


if __name__ == "__main__":
    main()
