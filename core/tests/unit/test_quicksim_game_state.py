"""Game state changes the match (US3, research R4, R5, R7; SC-006)."""

import random
from collections import Counter
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.calibration.metrics import late_goal_rates
from manager_core.competition.results import Result
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import _Side, simulate_match
from manager_core.quicksim.params import load_params
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.ratings import player_composites
from manager_core.quicksim.report import GOAL_KINDS, MatchReport

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MIDTABLE = ["ferroviario", "mineracao", "pedra-branca", "rio-turvo", "uniao-operaria"]


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


@pytest.fixture(scope="module")
def matches(provider: QuickSimProvider) -> list[tuple[Result, MatchReport]]:
    pairs = list(permutations(MIDTABLE, 2))
    out = []
    for n in range(4000):
        home, away = pairs[n % len(pairs)]
        out.append(simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                                  provider.dataset.players, provider.params,
                                  random.Random(f"state:{n}")))
    return out


def test_goals_by_period(matches: list[tuple[Result, MatchReport]]) -> None:
    periods: Counter[int] = Counter()
    for _, report in matches:
        for e in report.events:
            if e.kind in GOAL_KINDS:
                periods[min((e.minute.base - 1) // 15, 5)] += 1
    assert periods[5] == max(periods.values())  # 76-90+ has the most goals
    assert periods[0] == min(periods.values())  # 1-15 the fewest


def _late_goal_rates(matches: list[tuple[Result, MatchReport]]) -> dict[int, float]:
    return late_goal_rates(report for _, report in matches)


def test_trailing_side_pushes_and_is_exposed(provider: QuickSimProvider) -> None:
    """A club against itself at a neutral venue, so every state is equally strong: late on, a
    side one goal down scores more than a level side, and concedes more (its opponent, one
    goal up, scores more than a level side)."""
    sheet = provider.team_sheet("mineracao")
    mirrored = [simulate_match(sheet, sheet, provider.dataset.players, provider.params,
                               random.Random(f"mirror:{n}"), neutral=True)
                for n in range(6000)]
    rates = _late_goal_rates(mirrored)
    assert rates[-1] > rates[0] * 1.08
    assert rates[1] > rates[0]


def test_ten_men_take_fewer_points(provider: QuickSimProvider,
                                   matches: list[tuple[Result, MatchReport]]) -> None:
    with_red = without = 0.0
    n_red = n_clean = 0
    for result, report in matches:
        home_red = report.home.reds > 0 and report.away.reds == 0
        points = 3 if result.home_goals > result.away_goals else (
            1 if result.home_goals == result.away_goals else 0)
        if home_red:
            with_red += points
            n_red += 1
        elif report.home.reds == report.away.reds == 0:
            without += points
            n_clean += 1
    assert n_red > 100
    assert with_red / n_red < without / n_clean


def test_substitution_rules(matches: list[tuple[Result, MatchReport]]) -> None:
    per_side = []
    for _, report in matches:
        for side in ("home", "away"):
            subs = [e for e in report.events if e.kind == "sub" and e.side == side]
            assert len(subs) <= 5
            assert len({e.minute for e in subs if e.minute.base != 46}) <= 3
            came_on = {e.other_player_id for e in subs}
            assert not any(e.player_id in came_on for e in subs)  # no sub withdrawn again
            per_side.append(len(subs))
    mean = sum(per_side) / len(per_side)
    assert 3.0 <= mean <= 5.0


def test_caution_cuts_second_yellows(provider: QuickSimProvider) -> None:
    on = load_params()
    off = on.with_values(**{"caution.enabled": False})
    rates = []
    for params in (on, off):
        booked = second = 0
        for n in range(3000):
            _, report = simulate_match(provider.team_sheet("alvorada"),
                                       provider.team_sheet("serra-negra"),
                                       provider.dataset.players, params,
                                       random.Random(f"caution:{n}"))
            booked += sum(1 for e in report.events if e.kind == "yellow")
            second += sum(1 for e in report.events if e.kind == "second_yellow")
        rates.append(second / booked)
    assert rates[0] <= 0.75 * rates[1]  # SC-006


def test_caution_has_a_defensive_cost(provider: QuickSimProvider) -> None:
    """The trade-off (Constitution V): a booked defender lowers his side's defence rating
    when the behaviour is on, and not when it is off."""
    params = load_params()
    sheet = provider.team_sheet("vale-do-ouro")
    for enabled, expect_drop in ((True, True), (False, False)):
        p = params.with_values(**{"caution.enabled": enabled})
        side = _Side("home", sheet, provider.dataset.players, dict(sheet.starters),
                     list(sheet.bench))
        side.composites = {pid: player_composites(provider.dataset.player(pid))
                           for pid in {*side.on.values(), *side.bench}}
        side.refresh(p)
        before = side.ratings.defence
        defender = next(pid for i, pid in sheet.starters
                        if sheet.slot_position(i) is Position.DC)
        side.yellows[defender] = 1
        side.refresh(p)
        assert (side.ratings.defence < before) is expect_drop
