"""
Query history — user-friendly enhancement (see ENHANCEMENTS.md).

Status: 🟢 runnable today. Wired into main.py as:
    GET /history

In-memory only — resets on server restart. For persistence across restarts,
swap `_history` for a small SQLite table or a database of your choice; the
public functions (`record`, `all_entries`, `clear`) are the only surface
main.py depends on, so the storage backend can change without touching
main.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class HistoryEntry:
    query: str
    timestamp: float
    duration_seconds: float
    total_spent: float
    sections_count: int


_history: list[HistoryEntry] = []
_MAX_ENTRIES = 100  # simple cap so this doesn't grow unbounded in a long demo session


def record(query: str, duration_seconds: float, total_spent: float, sections_count: int) -> None:
    _history.append(HistoryEntry(
        query=query,
        timestamp=time.time(),
        duration_seconds=duration_seconds,
        total_spent=total_spent,
        sections_count=sections_count,
    ))
    if len(_history) > _MAX_ENTRIES:
        _history.pop(0)


def all_entries() -> list[dict]:
    return [entry.__dict__ for entry in reversed(_history)]  # most recent first


def clear() -> None:
    _history.clear()
