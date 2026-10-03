"""US4: the season calendar covers the year with matches, events and reserved windows."""

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.calendar import (
    SeasonCalendar,
    blocked_days,
    easter,
    reserved_windows,
)
from manager_core.competition.season import Season


@pytest.fixture(scope="module")
def season() -> Season:
    loaded = api.load_dataset(Path(__file__).resolve().parents[3] / "data" / "sample")
    assert loaded.dataset is not None
    s = api.start_season(loaded.dataset, "mg-modulo-i-2026", 2027, 20261002)
    api.advance_to(s, date(2027, 12, 31))
    return s


@pytest.mark.parametrize(("year", "length"), [(2027, 365), (2028, 366)])
def test_every_day_of_the_year(year: int, length: int) -> None:
    cal = SeasonCalendar.build(year)
    assert len(cal.days) == length
    assert cal.days[0].day == date(year, 1, 1) and cal.days[-1].day == date(year, 12, 31)
    assert all(b.day - a.day == timedelta(days=1) for a, b in pairwise(cal.days))
    assert cal.day(date(year, 7, 4)).day == date(year, 7, 4)
    assert sum(len(cal.month(m)) for m in range(1, 13)) == length


def _labels(cal: SeasonCalendar, day: date) -> set[str]:
    return {w.label for w in cal.day(day).windows}


def test_fixed_per_year_and_easter_windows_are_labelled() -> None:
    cal = SeasonCalendar.build(2027)
    assert "brasileirao" in _labels(cal, date(2027, 7, 1))  # fixed
    assert "copa-do-brasil" in _labels(cal, date(2027, 3, 1))
    assert "fifa" in _labels(cal, date(2027, 3, 22))  # from brazil-2027.toml
    assert "fifa" not in _labels(cal, date(2027, 3, 31))  # the fixed default is replaced
    assert "semana-santa" in _labels(cal, easter(2027) - timedelta(days=1))  # Easter-based


def test_years_without_a_file_use_the_default_fifa_windows() -> None:
    fifa = [w for w in reserved_windows(2029) if w.label == "fifa"]
    assert len(fifa) == 5
    assert fifa[0].start == date(2029, 3, 23) and fifa[0].blocks == ("state",)


def test_carnival_2027() -> None:
    cal = SeasonCalendar.build(2027)
    carnival = [d.day for d in cal.days if "carnaval" in {w.label for w in d.windows}]
    assert carnival == [date(2027, 2, d) for d in range(6, 11)]
    blocked = {d.day for d in cal.days if d.blocks_state}
    assert date(2027, 2, 8) in blocked and date(2027, 2, 9) in blocked
    assert date(2027, 2, 6) not in blocked


def test_no_state_match_on_carnival_monday_or_tuesday(season: Season) -> None:
    cal = season.calendar()
    for day in (date(2027, 2, 8), date(2027, 2, 9)):
        assert cal.day(day).match_ids == ()


def test_matchdays_carry_matches_and_events(season: Season) -> None:
    cal = season.calendar()
    listed = [m for d in cal.days for m in d.match_ids]
    assert sorted(listed) == sorted(season.matches)
    for d in cal.days:
        for match_id in d.match_ids:
            assert season.matches[match_id].kickoff.date() == d.day
    assert [e for d in cal.days for e in d.events] == sorted(season.events, key=lambda e: e.day)
    kinds = {e.kind for d in cal.days for e in d.events}
    assert {"draw", "qualified", "relegated", "champion"} <= kinds


def test_no_match_on_a_blocking_day(season: Season) -> None:
    blocked = blocked_days(2027, season.ruleset.calendar.avoid_windows)
    for d in season.calendar().days:
        if d.match_ids:
            assert d.day not in blocked
            assert not d.blocks_state


def test_knockout_dates_are_held_before_pairing() -> None:
    loaded = api.load_dataset(Path(__file__).resolve().parents[3] / "data" / "sample")
    assert loaded.dataset is not None
    s = api.start_season(loaded.dataset, "mg-modulo-i-2026", 2027, 20261002)
    held = {stage for d in s.calendar().days for stage in d.reserved_stages}
    assert held == {"semifinal", "final", "inconfidencia-semifinal", "inconfidencia-final"}
    api.advance_to(s, date(2027, 12, 31))
    assert not any(d.reserved_stages for d in s.calendar().days)


def test_month_out_of_range(season: Season) -> None:
    with pytest.raises(api.NotFoundError):
        api.season_calendar(season, 13)
    assert len(api.season_calendar(season, 2)) == 28
    assert len(api.season_calendar(season)) == 365
