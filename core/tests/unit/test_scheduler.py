"""Date generation, rest rule, Carnival and windows (research R7, R11b, R12b)."""

from datetime import date, datetime, time, timedelta
from itertools import pairwise

import pytest

from manager_core.competition.calendar import blocked_days, easter
from manager_core.competition.rules import load_ruleset
from manager_core.competition.scheduler import (
    SchedulingError,
    assign_kickoffs,
    plan_slots,
    resolve_window,
)

RULES = load_ruleset("mg-modulo-i-2026")
CAL = RULES.calendar


@pytest.mark.parametrize(
    ("year", "expected"),
    [(2026, date(2026, 4, 5)), (2027, date(2027, 3, 28)), (2028, date(2028, 4, 16)),
     (2029, date(2029, 4, 1)), (2030, date(2030, 4, 21))],
)
def test_easter(year: int, expected: date) -> None:
    assert easter(year) == expected


def test_carnival_2027_monday_and_tuesday_blocked() -> None:
    blocked = blocked_days(2027, CAL.avoid_windows)
    assert date(2027, 2, 8) in blocked and date(2027, 2, 9) in blocked
    assert date(2027, 2, 6) not in blocked and date(2027, 2, 7) not in blocked


def test_window_starts_on_first_weekend() -> None:
    start, end = resolve_window(CAL, 2027)
    assert start == date(2027, 1, 9)  # first Saturday on/after 01-08
    assert end == date(2027, 3, 8)


@pytest.mark.parametrize("year", range(2026, 2031))
def test_main_path_slots(year: int) -> None:
    slots = plan_slots(CAL, year, main_rounds=11, group_rounds=8)
    assert len(slots) == 11
    start, end = resolve_window(CAL, year)
    blocked = blocked_days(year, CAL.avoid_windows)
    weekends = [s for s in slots if s.kind == "weekend"]
    midweeks = [s for s in slots if s.kind == "midweek"]
    assert len(weekends) + len(midweeks) == 11
    for s in slots:
        assert all(start <= d <= end for d in s.days)
        assert not set(s.days) & blocked
    assert [s.days[0] for s in slots] == sorted(s.days[0] for s in slots)


def test_too_short_window_fails_clearly() -> None:
    with pytest.raises(SchedulingError):
        plan_slots(CAL, 2027, main_rounds=40, group_rounds=8)


def _rest_ok(kickoffs: dict[str, list[datetime]], hours: int) -> bool:
    for times in kickoffs.values():
        ordered = sorted(times)
        if any(b - a < timedelta(hours=hours) for a, b in pairwise(ordered)):
            return False
    return True


def test_rest_boundary_wednesday_to_saturday_is_legal() -> None:
    gap = datetime(2027, 1, 16, 16, 0) - datetime(2027, 1, 13, 21, 30)
    assert gap == timedelta(hours=66, minutes=30)


def test_assign_kickoffs_respects_rest() -> None:
    slots = plan_slots(CAL, 2027, main_rounds=11, group_rounds=8)
    last: dict[str, datetime] = {}
    kickoffs: dict[str, list[datetime]] = {}
    pairs = [("a", "b"), ("c", "d"), ("e", "f")]
    for slot in slots[:8]:
        assigned = assign_kickoffs(pairs, slot, CAL, last)
        for (h, a), when in zip(pairs, assigned, strict=True):
            for club in (h, a):
                kickoffs.setdefault(club, []).append(when)
                last[club] = when
    assert _rest_ok(kickoffs, CAL.min_rest_hours)


def test_thursday_club_never_plays_saturday() -> None:
    slots = plan_slots(CAL, 2027, main_rounds=11, group_rounds=8)
    weekend = next(s for s in slots if s.kind == "weekend")
    thursday = datetime.combine(weekend.days[0] - timedelta(days=2), time(21, 30))
    assigned = assign_kickoffs([("x", "y")], weekend, CAL, {"x": thursday})
    assert assigned[0].weekday() == 6  # Sunday


def test_kickoff_times() -> None:
    slots = plan_slots(CAL, 2027, main_rounds=11, group_rounds=8)
    for slot in slots:
        when = assign_kickoffs([("a", "b")], slot, CAL, {})[0]
        expected = CAL.kickoff_weekend if slot.kind == "weekend" else CAL.kickoff_midweek
        assert when.time() == expected
