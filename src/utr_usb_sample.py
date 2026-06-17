#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USB sample default entry point.

既存実装は `utr_usb_sample_legacy.py` から読み込みます。
通常実行時は、送信出力一時変更つきInventoryフローを起動します。

ポイント:
- 旧実装をこのモジュールの globals() に exec するため、既存テストの monkeypatch 互換性を維持します。
- 実行入口の main() だけを新しいInventoryフローに差し替えます。
"""

from __future__ import annotations

from pathlib import Path

_LEGACY_PATH = Path(__file__).with_name("utr_usb_sample_legacy.py")
_ORIGINAL_NAME = globals().get("__name__", "__main__")

# このファイルを直接実行した場合でも、legacy側の if __name__ == "__main__" が
# 誤って動かないよう、legacy読み込み中だけ __name__ を退避します。
globals()["__name__"] = "utr_usb_sample_legacy_loaded"
try:
    exec(compile(_LEGACY_PATH.read_text(encoding="utf-8"), str(_LEGACY_PATH), "exec"), globals())
finally:
    globals()["__name__"] = _ORIGINAL_NAME


def main() -> None:
    """送信出力一時変更つきInventoryフローを起動します。"""
    try:
        from src.utr_usb_inventory_with_output_power import main as integrated_main
    except ModuleNotFoundError:
        from utr_usb_inventory_with_output_power import main as integrated_main

    integrated_main()


if __name__ == "__main__":
    main()
