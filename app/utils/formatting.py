from __future__ import annotations

from datetime import datetime


def format_bytes(value: int | float) -> str:
    size = float(max(value, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Not available"
    return value.strftime("%Y-%m-%d %I:%M %p")


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return "<1 sec"
    if seconds < 60:
        return f"{seconds:.0f} sec"
    minutes = int(seconds // 60)
    remaining = int(seconds % 60)
    return f"{minutes}m {remaining}s"
