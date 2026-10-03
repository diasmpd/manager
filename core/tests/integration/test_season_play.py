"""US2: whole seasons played to the end (SC-001, SC-002)."""

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.season import Season
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
END = date(2027, 12, 31)


@pytest.fixture(scope="module")
def world() -> Dataset:
    dataset = api.load_dataset(SAMPLE).dataset
    assert dataset is not None
    return dataset


def _play(world: Dataset, seed: int) -> Season:
    season = api.start_season(world, "mg-modulo-i-2026", 2027, seed)
    api.advance_to(season, END)
    return season


def _check(season: Season) -> None:
    out = api.season_outcomes(season)
    assert out is not None
    overall = [r.club_id for r in api.season_table(season)]
    assert len(overall) == 12
    semis = set(out.main_entrants)
    assert len(semis) == 4
    assert out.champion in semis and out.runner_up in semis and out.champion != out.runner_up
    # group winners + best second are the semifinalists
    winners = {api.season_table(season, g.label)[0].club_id for g in api.season_groups(season)}
    assert winners <= semis
    # Inconfidência: first four non-semifinalists from 5th place on; never overlapping
    inc = out.side_entrants["inconfidencia"]
    assert not set(inc) & semis
    assert inc == [c for c in overall[4:] if c not in semis][:4]
    assert out.side_titles["inconfidencia"] in inc
    # relegation: 11th and 12th overall
    assert out.relegated == overall[10:12]
    # dates: knockout after first phase; rest everywhere; only the Inconfidência final after window
    matches = api.season_fixtures(season)
    group_end = max(m.kickoff for m in matches if m.stage_id == "primeira-fase")
    window_end = date(2027, 3, 8)
    by_club: dict[str, list] = {}
    for m in matches:
        assert m.result is not None
        if m.stage_id != "primeira-fase":
            assert m.kickoff > group_end
        if m.kickoff.date() > window_end:
            assert m.stage_id == "inconfidencia-final"
        for c in (m.home_id, m.away_id):
            by_club.setdefault(c, []).append(m.kickoff)
    for times in by_club.values():
        assert all(b - a >= timedelta(hours=66) for a, b in pairwise(sorted(times)))


@pytest.mark.parametrize("seed", range(200))
def test_full_season_invariants(world: Dataset, seed: int) -> None:
    _check(_play(world, seed))


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(200, 1000))
def test_full_season_invariants_1000(world: Dataset, seed: int) -> None:
    _check(_play(world, seed))


def test_replay_is_identical(world: Dataset) -> None:
    a, b = _play(world, 11), _play(world, 11)
    assert api.season_outcomes(a) == api.season_outcomes(b)
    assert api.season_fixtures(a) == api.season_fixtures(b)
    assert api.season_bracket(a) == api.season_bracket(b)


def test_results_are_placeholder(world: Dataset) -> None:
    season = _play(world, 3)
    assert {m.result.source for m in api.season_fixtures(season) if m.result} == {"placeholder"}


def test_final_at_neutral_venue(world: Dataset) -> None:
    season = _play(world, 4)
    final = [m for m in api.season_fixtures(season) if m.stage_id == "final"]
    assert len(final) == 1 and final[0].venue == "Arena Estadual das Gerais"
