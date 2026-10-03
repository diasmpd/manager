"""The quick-sim engine: determinism, invariants, home advantage, strength (US1)."""

import random
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.params import load_params
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import check_invariants

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def _play(provider: QuickSimProvider, home: str, away: str, seed: object,
          neutral: bool = False) -> tuple:
    return simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                          provider.dataset.players, provider.params, random.Random(str(seed)),
                          neutral)


def test_deterministic_per_seed(provider: QuickSimProvider) -> None:
    a = _play(provider, "alvorada", "sertanejo", 7)
    b = _play(provider, "alvorada", "sertanejo", 7)
    assert a == b
    assert len({_play(provider, "alvorada", "sertanejo", s)[1] for s in range(20)}) > 1


def test_invariants_hold_on_2000_matches(provider: QuickSimProvider) -> None:
    clubs = sorted(provider.dataset.clubs)
    pairs = list(permutations(clubs, 2))
    for n in range(2000):
        home, away = pairs[n % len(pairs)]
        result, report = _play(provider, home, away, f"inv:{n}")
        assert check_invariants(report, result) == [], (home, away, n)
        assert result.source == "quick_sim" and result.has_cards


def test_neutral_venue_removes_home_advantage(provider: QuickSimProvider) -> None:
    home_goals = away_goals = 0
    clubs = ["mineracao", "pedra-branca", "rio-turvo", "uniao-operaria"]
    for n in range(500):
        for a, b in permutations(clubs, 2):
            result, _ = _play(provider, a, b, f"neutral:{n}:{a}:{b}", neutral=True)
            home_goals += result.home_goals
            away_goals += result.away_goals
    ratio = home_goals / away_goals
    # ±6% (about 4 standard errors over 6,000 independent matches); with home advantage the
    # ratio is about 1.45
    assert 0.94 < ratio < 1.06


def test_home_advantage_exists(provider: QuickSimProvider) -> None:
    home_goals = away_goals = 0
    for n in range(1000):
        result, _ = _play(provider, "mineracao", "rio-turvo", f"h:{n}")
        home_goals += result.home_goals
        result, _ = _play(provider, "rio-turvo", "mineracao", f"a:{n}")
        away_goals += result.away_goals
    assert home_goals > away_goals * 1.15  # each club scores more at home


def test_stronger_side_wins_more(provider: QuickSimProvider) -> None:
    wins = losses = 0
    for n in range(1000):
        result, _ = _play(provider, "vale-do-ouro", "sertanejo", f"s:{n}", neutral=True)
        wins += result.home_goals > result.away_goals
        losses += result.home_goals < result.away_goals
    assert wins > 3 * losses
    assert losses > 0  # upsets exist


def test_bundled_params_are_used_by_default(provider: QuickSimProvider) -> None:
    assert provider.params == load_params()
