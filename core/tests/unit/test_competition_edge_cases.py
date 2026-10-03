"""Edge cases found in the 002 review (owner decision 2026-10-03: follow the suggested fixes)."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.calendar import easter, merge_windows
from manager_core.competition.rules import load_ruleset_file
from manager_core.competition.scheduler import WEEKEND, _slots, resolve_window
from manager_core.competition.season import Season
from manager_core.domain.dataset import Dataset

ROOT = Path(__file__).resolve().parents[2]
LIGA = ROOT / "src" / "manager_core" / "reference" / "competitions" / "test-liga-unica.toml"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    return loaded.dataset


# ---- 1. several relegation rules accumulate ----------------------------------------------


def test_several_relegation_rules_all_apply(world: Dataset, tmp_path: Path) -> None:
    text = LIGA.read_text("utf-8").replace(
        'outcomes = [{ kind = "relegated", overall_places = [8, 8] }]',
        'outcomes = [{ kind = "relegated", overall_places = [7, 7] },\n'
        '            { kind = "relegated", overall_places = [8, 8] }]')
    path = tmp_path / "two-rules.toml"
    path.write_text(text, "utf-8")
    ruleset = load_ruleset_file(path)
    season = Season.start(world, ruleset, 2027, 3, sorted(world.clubs)[:8])
    season.advance_to(date(2027, 12, 31))
    assert season.relegated == list(season.overall[6:8])  # 7th and 8th, in table order
    outcome = season.outcome()
    assert outcome is not None and outcome.relegated == list(season.overall[6:8])


# ---- 2. a weekend block that wraps round the week ----------------------------------------

SUN, MON, SAT = 6, 0, 5


def test_sunday_monday_slots_are_consecutive_days() -> None:
    start = date(2027, 1, 3)  # a Sunday
    slots = _slots((SUN, MON), WEEKEND, start, date(2027, 3, 1), frozenset())  # a Monday
    assert slots
    for slot in slots:
        assert [d.weekday() for d in slot.days] == [SUN, MON]
        assert slot.days[1] - slot.days[0] == timedelta(days=1)


def test_saturday_sunday_unchanged() -> None:
    slots = _slots((SAT, SUN), WEEKEND, date(2027, 1, 1), date(2027, 1, 31), frozenset())
    assert [tuple(d.weekday() for d in s.days) for s in slots] == [(SAT, SUN)] * 5
    assert slots[0].days[0] == date(2027, 1, 2)


def test_window_opens_on_the_first_day_of_a_wrapping_weekend(tmp_path: Path) -> None:
    text = LIGA.read_text("utf-8").replace('weekend_days = ["sat", "sun"]',
                                           'weekend_days = ["sun", "mon"]')
    path = tmp_path / "sun-mon.toml"
    path.write_text(text, "utf-8")
    ruleset = load_ruleset_file(path)
    start, _ = resolve_window(ruleset.calendar, 2027)
    assert start.weekday() == SUN and start >= date(2027, 1, 15)


# ---- 3. a per-year calendar file replaces fixed and Easter windows by label ----------------


def _window(label: str, start: str, end: str) -> dict[str, object]:
    return {"label": label, "name": label, "from": start, "to": end}


def _easter(label: str, offset_from: int, offset_to: int) -> dict[str, object]:
    return {"label": label, "name": label, "offset_from": offset_from, "offset_to": offset_to}


def test_year_file_replaces_easter_windows_by_label() -> None:
    fixed = {"easter_windows": [_easter("carnaval", -50, -46), _easter("semana-santa", -3, 0)]}
    specific = {"easter_windows": [_easter("carnaval", -51, -46)]}  # that year's dates
    windows = merge_windows(2027, fixed, specific)
    carnival = [w for w in windows if w.label == "carnaval"]
    assert len(carnival) == 1
    assert carnival[0].start == easter(2027) - timedelta(days=51)
    assert any(w.label == "semana-santa" for w in windows)  # other labels stay


def test_year_file_replaces_across_kinds() -> None:
    """A label is one window whatever its kind: a dated window in the year file replaces an
    Easter-based fixed window with the same label, and vice versa."""
    fixed = {"windows": [_window("fifa", "03-23", "03-31")],
             "easter_windows": [_easter("carnaval", -50, -46)]}
    specific = {"windows": [_window("carnaval", "02-06", "02-10")],
                "easter_windows": [_easter("fifa", -10, -5)]}
    windows = merge_windows(2027, fixed, specific)
    assert [(w.label, w.start) for w in windows if w.label == "carnaval"] == [
        ("carnaval", date(2027, 2, 6))]
    assert [(w.label, w.start) for w in windows if w.label == "fifa"] == [
        ("fifa", easter(2027) - timedelta(days=10))]


def test_without_a_year_file_fixed_windows_stay() -> None:
    fixed = {"windows": [_window("fifa", "03-23", "03-31")],
             "easter_windows": [_easter("carnaval", -50, -46)]}
    assert {w.label for w in merge_windows(2027, fixed, None)} == {"fifa", "carnaval"}
