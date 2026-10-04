"""Score-dependent openness (spec 006 T011, owner decision): a goalless game opens up as it goes
on, and a side that has just conceded responds. Real totals are under-dispersed (variance/mean
0.89 in Série A 2024-25), so these pull totals away from 0 and 1. Paired seeds."""

import random
from collections import Counter
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.params import ModelParams
from manager_core.quicksim.provider import QuickSimProvider

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MIDTABLE = ["ferroviario", "mineracao", "pedra-branca", "rio-turvo", "uniao-operaria"]
N = 1500


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset, ai_styles=False)


def _totals(provider: QuickSimProvider, params: ModelParams) -> Counter[int]:
    pairs = list(permutations(MIDTABLE, 2))
    totals: Counter[int] = Counter()
    for n in range(N):
        home, away = pairs[n % len(pairs)]
        result, _ = simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                                   provider.dataset.players, params,
                                   random.Random(f"openness:{n}"))
        totals[min(result.home_goals + result.away_goals, 5)] += 1
    return totals


def _without(provider: QuickSimProvider) -> ModelParams:
    return provider.params.with_values(**{"state.goalless": 0.0, "state.respond": 0.0})


def test_a_goalless_game_opens_up(provider: QuickSimProvider) -> None:
    off = _totals(provider, _without(provider))
    on = _totals(provider, _without(provider).with_values(**{"state.goalless": 0.3}))
    assert on[0] < off[0] * 0.8  # fewer 0-0s
    assert on[0] + on[1] < off[0] + off[1]


def test_a_side_that_concedes_responds(provider: QuickSimProvider) -> None:
    off = _totals(provider, _without(provider))
    on = _totals(provider, _without(provider).with_values(**{"state.respond": 0.3}))
    assert on[0] == off[0]  # nothing to respond to in a 0-0
    assert on[1] < off[1]  # fewer 1-0s stay 1-0
    assert sum(k * v for k, v in on.items()) > sum(k * v for k, v in off.items())
