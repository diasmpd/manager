"""Score-dependent openness (spec 006 T011, owner decision): a goalless game opens up as it goes
on, and once a match has 3+ goals both sides manage it. Real totals are under-dispersed
(variance/mean 0.89 in Série A 2024-25). Paired seeds."""

import random
from collections import Counter
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.params import ModelParams
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import GOAL_KINDS

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MIDTABLE = ["ferroviario", "mineracao", "pedra-branca", "rio-turvo", "uniao-operaria"]
N = 1500


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset, ai_styles=False)


def _play(provider: QuickSimProvider, params: ModelParams) -> tuple[Counter[int], float]:
    """Goal totals (5 = 5+) and the share of goals after minute 75."""
    pairs = list(permutations(MIDTABLE, 2))
    totals: Counter[int] = Counter()
    late = goals = 0
    for n in range(N):
        home, away = pairs[n % len(pairs)]
        result, report = simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                                        provider.dataset.players, params,
                                        random.Random(f"openness:{n}"))
        totals[min(result.home_goals + result.away_goals, 5)] += 1
        for e in report.events:
            if e.kind in GOAL_KINDS:
                goals += 1
                late += e.minute.base > 75
    return totals, late / goals


def _without(provider: QuickSimProvider) -> ModelParams:
    return provider.params.with_values(**{"state.goalless": 0.0, "state.managed": 0.0})


def test_a_goalless_game_opens_up(provider: QuickSimProvider) -> None:
    off, _ = _play(provider, _without(provider))
    on, _ = _play(provider, _without(provider).with_values(**{"state.goalless": 0.3}))
    assert on[0] < off[0] * 0.8  # fewer 0-0s
    assert on[0] + on[1] < off[0] + off[1]


def test_a_high_scoring_game_is_managed(provider: QuickSimProvider) -> None:
    off, late_off = _play(provider, _without(provider))
    on, late_on = _play(provider, _without(provider).with_values(**{"state.managed": 0.3}))
    assert [on[k] for k in range(3)] == [off[k] for k in range(3)]  # same until a third goal
    assert on[5] < off[5]  # fewer 5+ games
    assert on[3] > off[3]  # more of them stop at three
    assert late_on <= late_off  # the late-goal share does not rise
