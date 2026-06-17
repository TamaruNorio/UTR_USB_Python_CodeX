#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UTR USB sample default entry point.

既存実装は `utr_usb_sample_legacy.py` から読み込みます。
通常実行時は、送信出力一時変更つきInventoryフローを起動します。

ポイント:
- 旧実装をこのモジュールの globals() に読み込むため、既存テストの monkeypatch 互換性を維持します。
- legacy側の `if __name__ == '__main__': main()` は実行しません。
- 実行入口の main() だけを新しいInventoryフローに差し替えます。
"""

from __future__ import annotations

from pathlib import Path

_LEGACY_PATH = Path(__file__).with_name("utr_usb_sample_legacy.py")
_LEGACY_SOURCE = _LEGACY_PATH.read_text(encoding="utf-8")

# legacyファイル末尾の直接実行ブロックだけを外して、このモジュールへ読み込みます。
# __name__ を変更しないため、dataclassや既存テストのmonkeypatch互換性を維持できます。
for _guard in ("\nif __name__ == '__main__':", '\nif __name__ == "__main__":'):
    if _guard in _LEGACY_SOURCE:
        _LEGACY_SOURCE = _LEGACY_SOURCE.rsplit(_guard, maxsplit=1)[0]
        break

exec(compile(_LEGACY_SOURCE, str(_LEGACY_PATH), "exec"), globals())


def main() -> None:
    """送信出力一時変更つきInventoryフローを起動します。"""
    try:
        from src.utr_usb_inventory_with_output_power import main as integrated_main
    except ModuleNotFoundError:
        from utr_usb_inventory_with_output_power import main as integrated_main

    integrated_main()


if __name__ == "__main__":
    main()
