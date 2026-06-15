"""Inventory result export helpers."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


CSV_FIELDNAMES = [
    "saved_at",
    "total_iterations",
    "total_read_time_seconds",
    "total_read_count",
    "average_read_count",
    "pc_uii",
    "read_count",
]


def build_result_summary(
    total_iterations: int,
    total_read_time: float,
    total_read_count: int,
    pc_uii_count_dict: dict[str, int],
    saved_at: str | None = None,
) -> dict[str, Any]:
    """Build a serializable summary of inventory results."""
    average_read_count = 0.0
    if total_iterations:
        average_read_count = total_read_count / total_iterations

    items = [
        {"pc_uii": pc_uii, "read_count": read_count}
        for pc_uii, read_count in sorted(pc_uii_count_dict.items())
    ]

    return {
        "saved_at": saved_at or datetime.now().isoformat(timespec="seconds"),
        "total_iterations": total_iterations,
        "total_read_time_seconds": total_read_time,
        "total_read_count": total_read_count,
        "average_read_count": average_read_count,
        "items": items,
    }


def _summary_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    base = {
        "saved_at": summary["saved_at"],
        "total_iterations": summary["total_iterations"],
        "total_read_time_seconds": summary["total_read_time_seconds"],
        "total_read_count": summary["total_read_count"],
        "average_read_count": summary["average_read_count"],
    }
    items = summary.get("items") or [{"pc_uii": "", "read_count": 0}]
    rows = []
    for item in items:
        rows.append(
            {
                **base,
                "pc_uii": item["pc_uii"],
                "read_count": item["read_count"],
            }
        )
    return rows


def save_results_to_csv(filename: str, summary: dict[str, Any]) -> None:
    """Append inventory summary rows to a UTF-8 BOM CSV file."""
    path = Path(filename)
    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(_summary_rows(summary))


def save_results_to_json(filename: str, summary: dict[str, Any]) -> None:
    """Append an inventory summary to a JSON history list."""
    path = Path(filename)
    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8") as file:
            history = json.load(file)
        if not isinstance(history, list):
            raise ValueError("JSON result file must contain a list")
    else:
        history = []

    history.append(summary)

    with path.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")
