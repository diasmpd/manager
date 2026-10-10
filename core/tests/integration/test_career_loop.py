"""US2: "Continuar" stops at events, before the user's matches and at the season end; it
autosaves every in-game week (spec 004, research R4)."""

import os
import random
import time
from datetime import timedelta
from itertools import pairwise
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import EVENT, SEASON_END, STOP_EVENTS, USER_MATCH, Career
from manager_core.career.store import AUTOSAVE, path_for
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _user_match_days(career: Career) -> set:
    return {m.kickoff.date() for m in career.season.matches.values()
            if career.user_club_id in (m.home_id, m.away_id)}


def test_first_continue_stops_before_the_first_user_match(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "loop", "alvorada", master_seed=11)
    first = min(_user_match_days(career))
    stop = api.continue_career(career, tmp_path)
    # the draw event comes first, a week before the window opens
    while stop.kind == EVENT:
        stop = api.continue_career(career, tmp_path)
    assert stop.kind == USER_MATCH and stop.day == first
    assert career.current_date == first - timedelta(days=1)
    match = career.season.matches[stop.match_id or ""]
    assert match.id not in career.season.results
    api.continue_career(career, tmp_path)
    assert match.id in career.season.results  # the next continue plays it


def test_every_stop_is_justified_and_no_user_match_is_skipped(world: Dataset,
                                                              tmp_path: Path) -> None:
    career = api.new_career(world, "stops", "serra-negra", master_seed=5)
    user_stops = []
    while True:
        before = career.current_date
        stop = api.continue_career(career, tmp_path)
        if stop.kind == USER_MATCH:
            user_stops.append(stop.day)
            assert career.current_date == stop.day - timedelta(days=1)
        elif stop.kind == EVENT:
            assert any(e.kind in STOP_EVENTS and e.day == stop.day for e in stop.events)
        else:
            assert stop.kind == SEASON_END and career.season.complete
            break
        # no user match was played without a stop before it
        played_days = {m.kickoff.date() for m in career.season.matches.values()
                       if m.id in career.season.results
                       and career.user_club_id in (m.home_id, m.away_id)}
        assert played_days <= set(user_stops)
        assert career.current_date >= before
    assert sorted(user_stops) == sorted(_user_match_days(career))


def test_weekly_autosave(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "auto", "alvorada", master_seed=2)
    seen = []
    for _ in range(12):
        api.continue_career(career, tmp_path)
        if path_for(tmp_path, AUTOSAVE).is_file():
            auto = api.load_career(tmp_path, AUTOSAVE)
            seen.append(auto.current_date)
    assert seen, "an autosave was written"
    dates = sorted(set(seen))
    assert all(b - a >= timedelta(days=7) for a, b in pairwise(dates))
    assert path_for(tmp_path, "auto").is_file()  # the named save is written too


def test_save_and_load_anywhere_continues_identically(world: Dataset, tmp_path: Path) -> None:
    """SC-001: save/load at random stops, then both play to the season end identically."""
    rng = random.Random(4)
    reference = api.new_career(world, "ref", "pedra-branca", master_seed=9)
    api.continue_career(reference, tmp_path / "ref", to_season_end=True)
    stops_to_try = sorted(rng.sample(range(1, 30), 8))
    career = api.new_career(world, "ref", "pedra-branca", master_seed=9)
    n = 0
    while career.pending is None or career.pending.kind != SEASON_END:
        n += 1
        api.continue_career(career, tmp_path / "x")
        if n in stops_to_try:
            api.save_career(career, tmp_path / "x")
            career = api.load_career(tmp_path / "x", "ref")
    assert career.season.results == reference.season.results
    assert career.season.outcome() == reference.season.outcome()


@pytest.mark.slow
def test_a_season_is_fast(world: Dataset, tmp_path: Path) -> None:
    """SC-002: a new career to the season end in under 5 s, autosaves included. This is the
    day loop's budget, so the user's matches stay on the quick sim here; on the positional
    engine they have their own budget (below)."""
    start = time.perf_counter()
    career = api.new_career(world, "rapido", "alvorada", master_seed=1)
    career.positional = False
    api.apply_selection(career)
    api.continue_career(career, tmp_path, to_season_end=True)
    # the budget is on the reference PC; CI runners scale it like the quick-sim budgets
    scale = float(os.environ.get("MANAGER_PERF_LIMIT_S", "2.0")) / 2.0
    assert time.perf_counter() - start < 5.0 * scale


@pytest.mark.slow
def test_a_season_with_positional_matches_is_within_budget(world: Dataset,
                                                           tmp_path: Path) -> None:
    """Spec 008 SC-004: a full season with the user's matches on the positional engine in at
    most 2 minutes."""
    start = time.perf_counter()
    career = api.new_career(world, "posicional", "alvorada", master_seed=1)
    assert career.positional
    api.continue_career(career, tmp_path, to_season_end=True)
    scale = float(os.environ.get("MANAGER_PERF_LIMIT_S", "2.0")) / 2.0
    assert time.perf_counter() - start < 120.0 * scale
