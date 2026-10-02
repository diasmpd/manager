"""Date generation (FR-011, research R7, R12b).

Rounds go into slots: a weekend slot (e.g. Saturday+Sunday) or a midweek slot
(Wednesday+Thursday). The main path uses every weekend in the window first; when there are
more rounds than weekends, midweek slots are spread evenly through the group stage. Inside a
slot, each match gets the day that keeps both clubs rested at least `min_rest_hours`, balancing
the matches across the slot's days.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from manager_core.competition.calendar import blocked_days
from manager_core.competition.rules import CalendarRule

WEEKEND = "weekend"
MIDWEEK = "midweek"


class SchedulingError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Slot:
    kind: str  # weekend / midweek
    days: tuple[date, ...]

    @property
    def first_day(self) -> date:
        return self.days[0]


def resolve_window(cal: CalendarRule, year: int) -> tuple[date, date]:
    """Window start = first weekend (its first day) on or after window_start."""
    start = date(year, *cal.window_start)
    first_weekend_day = min(cal.weekend_days)
    while start.weekday() != first_weekend_day:
        start += timedelta(days=1)
    return start, date(year, *cal.window_end)


def _slots(kind_days: tuple[int, ...], kind: str, start: date, end: date | None,
           blocked: frozenset[date], limit: int | None = None) -> list[Slot]:
    first = min(kind_days)
    d = start
    while d.weekday() != first:
        d += timedelta(days=1)
    slots: list[Slot] = []
    while (end is None or d <= end) and (limit is None or len(slots) < limit):
        days = tuple(
            d + timedelta(days=wd - first) for wd in sorted(kind_days)
            if (end is None or d + timedelta(days=wd - first) <= end)
            and d + timedelta(days=wd - first) not in blocked
        )
        if days:
            slots.append(Slot(kind, days))
        d += timedelta(days=7)
    return slots


def plan_slots(cal: CalendarRule, year: int, main_rounds: int, group_rounds: int) -> list[Slot]:
    start, end = resolve_window(cal, year)
    blocked = blocked_days(year, cal.avoid_windows)
    weekends = _slots(cal.weekend_days, WEEKEND, start, end, blocked)
    if main_rounds <= len(weekends):
        return weekends[:main_rounds]
    extra = main_rounds - len(weekends)
    if not weekends:
        raise SchedulingError("no weekend inside the window")
    midweeks = [
        s for s in _slots(cal.midweek_days, MIDWEEK, start, end, blocked)
        if weekends[0].first_day < s.first_day < weekends[-1].first_day
    ]
    # Prefer midweeks inside the group stage, where real Estadual tables put them.
    group_end = weekends[min(group_rounds, len(weekends)) - 1].first_day
    candidates = [s for s in midweeks if s.first_day < group_end] or midweeks
    if len(candidates) < extra:
        candidates = midweeks
    if len(candidates) < extra:
        raise SchedulingError(f"{main_rounds} rounds do not fit between {start} and {end}")
    step = len(candidates) / (extra + 1)
    picked: list[Slot] = []
    for k in range(extra):
        index = min(len(candidates) - 1, round((k + 1) * step) - 1)
        while candidates[index] in picked:
            index += 1
        picked.append(candidates[index])
    return sorted([*weekends, *picked], key=lambda s: s.first_day)


def next_weekend_after(cal: CalendarRule, year: int, after: date) -> Slot:
    """First free weekend slot after `after`, ignoring the window end (may_exceed_window)."""
    blocked = blocked_days(year, cal.avoid_windows)
    slots = _slots(cal.weekend_days, WEEKEND, after + timedelta(days=1), None, blocked, limit=1)
    if not slots:
        raise SchedulingError(f"no weekend after {after}")
    return slots[0]


def assign_kickoffs(pairs: Sequence[tuple[str, str]], slot: Slot, cal: CalendarRule,
                    last_played: Mapping[str, datetime]) -> list[datetime]:
    """One kick-off per pair inside the slot, respecting the minimum rest for both clubs."""
    kickoff = cal.kickoff_weekend if slot.kind == WEEKEND else cal.kickoff_midweek
    times = [datetime.combine(d, kickoff) for d in slot.days]
    rest = timedelta(hours=cal.min_rest_hours)

    def allowed(pair: tuple[str, str]) -> list[int]:
        return [i for i, when in enumerate(times)
                if all(club not in last_played or when - last_played[club] >= rest
                       for club in pair)]

    options = [allowed(p) for p in pairs]
    for pair, opts in zip(pairs, options, strict=True):
        if not opts:
            raise SchedulingError(f"no legal day for {pair[0]} x {pair[1]} in slot {slot.days}")
    load = [0] * len(times)
    result: list[datetime | None] = [None] * len(pairs)
    for index in sorted(range(len(pairs)), key=lambda i: (len(options[i]), i)):
        choice = min(options[index], key=lambda i: (load[i], i))
        load[choice] += 1
        result[index] = times[choice]
    return [r for r in result if r is not None]
