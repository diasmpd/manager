"""Scorers, assisters, penalty takers and cards per player (US2, research R5, R7)."""

import random
from collections import Counter
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import penalty_order, simulate_match
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.ratings import POSITION_GROUP, Group
from manager_core.quicksim.report import GOAL_KINDS, MatchReport

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MATCHES = 3000


@pytest.fixture(scope="module")
def sample() -> tuple[QuickSimProvider, list[MatchReport]]:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    provider = QuickSimProvider(loaded.dataset)
    pairs = list(permutations(sorted(loaded.dataset.clubs), 2))
    reports = []
    for n in range(MATCHES):
        home, away = pairs[n % len(pairs)]
        _, report = simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                                   provider.dataset.players, provider.params,
                                   random.Random(f"players:{n}"))
        reports.append(report)
    return provider, reports


def _slot_groups(report: MatchReport) -> dict[str, Group]:
    """Group of every player by his starting slot, or by the slot he came on in."""
    groups: dict[str, Group] = {}
    for side in ("home", "away"):
        lineup = report.lineup(side)
        for position, pid in lineup.starters:
            groups[pid] = POSITION_GROUP[position]
        for e in report.events:
            if e.kind == "sub" and e.side == side and e.other_player_id:
                groups[e.other_player_id] = groups.get(e.player_id, Group.MIDFIELDER)
    return groups


def test_goals_by_line(sample: tuple[QuickSimProvider, list[MatchReport]]) -> None:
    _, reports = sample
    by_group: Counter[Group] = Counter()
    for report in reports:
        groups = _slot_groups(report)
        for e in report.events:
            if e.kind in ("goal", "penalty_goal"):
                by_group[groups[e.player_id]] += 1
    assert by_group[Group.GOALKEEPER] == 0
    assert by_group[Group.FORWARD] > by_group[Group.MIDFIELDER] > by_group[Group.DEFENDER]
    total = sum(by_group.values())
    assert by_group[Group.FORWARD] / total > 0.35  # strikers score the most (FM, real data)


def test_assists(sample: tuple[QuickSimProvider, list[MatchReport]]) -> None:
    _, reports = sample
    open_play = [e for r in reports for e in r.events if e.kind == "goal"]
    assisted = [e for e in open_play if e.other_player_id]
    assert all(e.other_player_id != e.player_id for e in assisted)
    assert 0.70 <= len(assisted) / len(open_play) <= 0.80


def test_penalty_taker_is_the_best_on_the_pitch(
        sample: tuple[QuickSimProvider, list[MatchReport]]) -> None:
    provider, reports = sample
    seen = 0
    for report in reports:
        for e in report.events:
            if e.kind not in ("penalty_goal", "penalty_miss"):
                continue
            seen += 1
            taker = provider.dataset.player(e.player_id)
            groups = _slot_groups(report)
            outfield = [provider.dataset.player(p) for p in _on_pitch(report, e)
                        if groups.get(p) is not Group.GOALKEEPER]  # keepers do not take them
            best = penalty_order(outfield)[0]
            assert taker.attributes.get("penalty_taking") == best.attributes.get(
                "penalty_taking")
    assert seen > 50


def _on_pitch(report: MatchReport, event: object) -> list[str]:
    side = event.side  # type: ignore[attr-defined]
    on = {pid for _, pid in report.lineup(side).starters}
    for e in report.events:
        if e is event:
            break
        if e.side != side:
            continue
        if e.kind == "sub":
            on.discard(e.player_id)
            on.add(e.other_player_id or "")
        elif e.kind in ("red", "second_yellow"):
            on.discard(e.player_id)
    return sorted(on)


def test_cards_go_to_defenders_and_aggressive_players(
        sample: tuple[QuickSimProvider, list[MatchReport]]) -> None:
    provider, reports = sample
    by_group: Counter[Group] = Counter()
    cards: Counter[str] = Counter()
    appearances: Counter[str] = Counter()
    for report in reports:
        groups = _slot_groups(report)
        appearances.update(groups.keys())
        for e in report.events:
            if e.kind in ("yellow", "second_yellow", "red"):
                by_group[groups[e.player_id]] += 1
                cards[e.player_id] += 1
    assert by_group[Group.DEFENDER] + by_group[Group.MIDFIELDER] > 0.6 * sum(by_group.values())
    assert by_group[Group.GOALKEEPER] < 0.03 * sum(by_group.values())

    def rate(predicate: object) -> float:
        ids = [pid for pid in appearances if predicate(  # type: ignore[operator]
            provider.dataset.player(pid).attributes.get("aggression"))]
        return sum(cards[pid] for pid in ids) / sum(appearances[pid] for pid in ids)

    assert rate(lambda a: a >= 14) > 1.2 * rate(lambda a: a <= 7)  # per appearance


def test_goal_kinds_are_known(sample: tuple[QuickSimProvider, list[MatchReport]]) -> None:
    _, reports = sample
    kinds = Counter(e.kind for r in reports for e in r.events if e.kind in GOAL_KINDS)
    assert kinds["goal"] > kinds["penalty_goal"] > 0
    assert kinds["own_goal"] > 0
