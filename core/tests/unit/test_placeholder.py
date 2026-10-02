"""The placeholder provider: deterministic, plausible-looking, clearly labelled (FR-016).
Sanity checks only; realism is spec 003's job (not a calibration target)."""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import PLACEHOLDER, MatchContext, PlaceholderProvider
from manager_core.competition.seeds import sub_seed
from manager_core.domain.dataset import Dataset

CTX = MatchContext(season_seed=1, stage_id="x")


@pytest.fixture(scope="module")
def world() -> Dataset:
    dataset = api.load_dataset(Path(__file__).resolve().parents[3] / "data" / "sample").dataset
    assert dataset is not None
    return dataset


def _play(provider: PlaceholderProvider, world: Dataset, home: str, away: str, label: str):  # type: ignore[no-untyped-def]
    rng = random.Random(sub_seed(1, f"match:{label}"))
    return provider.play(label, world.club(home), world.club(away), CTX, rng)


def test_deterministic_per_match(world: Dataset) -> None:
    p = PlaceholderProvider(world)
    first = _play(p, world, "vale-do-ouro", "sertanejo", "m1")
    _play(p, world, "alvorada", "jequitiba", "m2")  # playing other matches changes nothing
    assert _play(p, world, "vale-do-ouro", "sertanejo", "m1") == first
    assert first.source == PLACEHOLDER


def test_plausible_scorelines(world: Dataset) -> None:
    p = PlaceholderProvider(world)
    clubs = sorted(world.clubs)
    goals = home_wins = away_wins = strong_wins = strong_games = 0
    for i in range(2000):
        home, away = clubs[i % 12], clubs[(i * 5 + 1) % 12]
        if home == away:
            continue
        r = _play(p, world, home, away, f"g{i}")
        goals += r.home_goals + r.away_goals
        home_wins += r.home_goals > r.away_goals
        away_wins += r.home_goals < r.away_goals
        stronger = home if p.strength(home) > p.strength(away) else away
        if abs(p.strength(home) - p.strength(away)) > 30:
            strong_games += 1
            winner = (home if r.home_goals > r.away_goals
                      else away if r.away_goals > r.home_goals else None)
            strong_wins += winner == stronger
    games = home_wins + away_wins + (2000 - home_wins - away_wins)
    assert 2.0 <= goals / games <= 3.2
    assert home_wins > away_wins
    assert strong_wins / strong_games > 0.5


def test_shootout_is_valid(world: Dataset) -> None:
    p = PlaceholderProvider(world)
    for i in range(50):
        rng = random.Random(i)
        s = p.shootout(f"s{i}", world.club("vale-do-ouro"), world.club("sertanejo"), CTX, rng)
        assert s.winner_id in ("vale-do-ouro", "sertanejo")
        assert len(s.kicks) >= 6
