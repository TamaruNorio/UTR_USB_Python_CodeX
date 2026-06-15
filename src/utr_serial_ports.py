"""Helpers for displaying and selecting serial ports without opening them."""

from typing import Any, Iterable, Optional


def _display_value(value: object) -> str:
    if value is None:
        return "不明"
    text = str(value).strip()
    return text if text else "不明"


def format_port_info(port: Any, index: int) -> list[str]:
    """Return user-facing lines for one serial port entry."""
    device = _display_value(getattr(port, "device", None))
    description = _display_value(getattr(port, "description", None))
    manufacturer = _display_value(getattr(port, "manufacturer", None))
    hwid = _display_value(getattr(port, "hwid", None))

    return [
        f"[{index}] {device}",
        f"    description : {description}",
        f"    manufacturer: {manufacturer}",
        f"    hwid        : {hwid}",
    ]


def normalize_port_input(value: str) -> str:
    """Normalize raw user input for matching."""
    return value.strip()


def is_quit_input(value: str) -> bool:
    """Return True when the user asked to quit selection."""
    return normalize_port_input(value).lower() == "q"


def find_port_by_user_input(user_input: str, ports: Iterable[Any]) -> Optional[Any]:
    """Find a port by zero-based index or COM device name."""
    normalized = normalize_port_input(user_input)
    port_list = list(ports)

    if not normalized or is_quit_input(normalized):
        return None

    if normalized.isdigit():
        index = int(normalized)
        if 0 <= index < len(port_list):
            return port_list[index]
        return None

    normalized_device = normalized.upper()
    for port in port_list:
        device = getattr(port, "device", None)
        if device is not None and str(device).strip().upper() == normalized_device:
            return port

    return None
