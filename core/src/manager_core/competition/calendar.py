"""Reserved calendar windows (research R11, R11b): fixed month-day ranges, per-year files and
Easter-based windows (Carnival, Holy Week)."""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from importlib import resources
from typing import Any

STATE = "state"


def easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous / Meeus-Jones-Butcher algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


@dataclass(frozen=True, slots=True)
class ReservedWindow:
    label: str
    name: str
    start: date
    end: date
    blocks: tuple[str, ...]

    def days(self) -> Iterable[date]:
        d = self.start
        while d <= self.end:
            yield d
            d += timedelta(days=1)


def _read(name: str) -> dict[str, Any] | None:
    entry = resources.files("manager_core.reference").joinpath("calendar").joinpath(name)
    if not entry.is_file():
        return None
    return tomllib.loads(entry.read_text("utf-8"))


def _month_day(year: int, raw: str) -> date:
    month, day = (int(p) for p in raw.split("-"))
    return date(year, month, day)


@cache
def reserved_windows(year: int) -> tuple[ReservedWindow, ...]:
    windows: list[ReservedWindow] = []
    for doc in (_read("brazil.toml"), _read(f"brazil-{year}.toml")):
        if doc is None:
            continue
        for w in doc.get("windows", []):
            windows.append(ReservedWindow(
                w["label"], w["name"], _month_day(year, w["from"]), _month_day(year, w["to"]),
                tuple(w.get("blocks", ())),
            ))
        anchor = easter(year)
        for w in doc.get("easter_windows", []):
            windows.append(ReservedWindow(
                w["label"], w["name"], anchor + timedelta(days=w["offset_from"]),
                anchor + timedelta(days=w["offset_to"]), tuple(w.get("blocks", ())),
            ))
    return tuple(sorted(windows, key=lambda w: (w.start, w.label)))


def blocked_days(year: int, avoid_labels: Iterable[str]) -> frozenset[date]:
    """Days on which no state match may be scheduled."""
    avoid = set(avoid_labels)
    blocked: set[date] = set()
    for w in reserved_windows(year):
        if STATE in w.blocks or w.label in avoid:
            blocked.update(w.days())
    return frozenset(blocked)
