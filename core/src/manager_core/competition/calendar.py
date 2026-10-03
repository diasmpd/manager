"""The season calendar (FR-019/020, research R11, R11b).

Reserved windows come from data: fixed month-day ranges in `brazil.toml`, an optional
`brazil-<year>.toml` whose windows replace the fixed ones with the same label (FIFA dates move
every year), and Easter-based windows (Carnival, Holy Week). `SeasonCalendar` lays a season's
matches, events and reserved dates over every day of the year.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from importlib import resources
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from manager_core.competition.season import SeasonEvent

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


def merge_windows(year: int, fixed: dict[str, Any] | None,
                  specific: dict[str, Any] | None) -> tuple[ReservedWindow, ...]:
    """Fixed windows plus the year's own file. A label in the year file (dated or Easter-based)
    replaces every fixed window with that label, whatever its kind."""
    replaced = {w["label"] for kind in ("windows", "easter_windows")
                for w in (specific or {}).get(kind, [])}
    windows: list[ReservedWindow] = []
    anchor = easter(year)
    for doc in (fixed, specific):
        if doc is None:
            continue
        for w in doc.get("windows", []):
            if doc is fixed and w["label"] in replaced:
                continue
            windows.append(ReservedWindow(
                w["label"], w["name"], _month_day(year, w["from"]), _month_day(year, w["to"]),
                tuple(w.get("blocks", ())),
            ))
        for w in doc.get("easter_windows", []):
            if doc is fixed and w["label"] in replaced:
                continue
            windows.append(ReservedWindow(
                w["label"], w["name"], anchor + timedelta(days=w["offset_from"]),
                anchor + timedelta(days=w["offset_to"]), tuple(w.get("blocks", ())),
            ))
    return tuple(sorted(windows, key=lambda w: (w.start, w.label)))


@cache
def reserved_windows(year: int) -> tuple[ReservedWindow, ...]:
    return merge_windows(year, _read("brazil.toml"), _read(f"brazil-{year}.toml"))


def blocked_days(year: int, avoid_labels: Iterable[str]) -> frozenset[date]:
    """Days on which no state match may be scheduled."""
    avoid = set(avoid_labels)
    blocked: set[date] = set()
    for w in reserved_windows(year):
        if STATE in w.blocks or w.label in avoid:
            blocked.update(w.days())
    return frozenset(blocked)


@dataclass(frozen=True, slots=True)
class CalendarDay:
    day: date
    match_ids: tuple[str, ...] = ()
    events: tuple[SeasonEvent, ...] = ()
    windows: tuple[ReservedWindow, ...] = ()
    reserved_stages: tuple[str, ...] = ()  # stage ids whose dates are held but not yet paired

    @property
    def blocks_state(self) -> bool:
        return any(STATE in w.blocks for w in self.windows)


@dataclass(frozen=True, slots=True)
class SeasonCalendar:
    """Every day of one year, 1 January to 31 December."""

    year: int
    days: tuple[CalendarDay, ...]

    @classmethod
    def build(cls, year: int, matches: Iterable[tuple[date, str]] = (),
              events: Iterable[SeasonEvent] = (),
              reserved: Iterable[tuple[date, str]] = ()) -> SeasonCalendar:
        by_match: dict[date, list[str]] = {}
        for day, match_id in matches:
            by_match.setdefault(day, []).append(match_id)
        by_event: dict[date, list[SeasonEvent]] = {}
        for event in events:
            by_event.setdefault(event.day, []).append(event)
        by_reserved: dict[date, list[str]] = {}
        for day, stage_id in reserved:
            if stage_id not in by_reserved.setdefault(day, []):
                by_reserved[day].append(stage_id)
        by_window: dict[date, list[ReservedWindow]] = {}
        for window in reserved_windows(year):
            for day in window.days():
                by_window.setdefault(day, []).append(window)
        days = []
        day = date(year, 1, 1)
        while day.year == year:
            days.append(CalendarDay(day, tuple(by_match.get(day, ())),
                                    tuple(by_event.get(day, ())),
                                    tuple(by_window.get(day, ())),
                                    tuple(by_reserved.get(day, ()))))
            day += timedelta(days=1)
        return cls(year, tuple(days))

    def day(self, day: date) -> CalendarDay:
        if day.year != self.year:
            raise KeyError(day)
        return self.days[(day - date(self.year, 1, 1)).days]

    def month(self, month: int) -> tuple[CalendarDay, ...]:
        if not 1 <= month <= 12:
            raise ValueError(f"month must be 1-12, got {month}")
        return tuple(d for d in self.days if d.day.month == month)
