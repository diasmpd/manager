"""Tactics move the quick sim the documented way (spec 006 FR-005, T008).

Each variant plays the same seeded fixtures as the baseline (default against default), with the
subject club alternating home and away, so the comparison is paired.
"""

import dataclasses
import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import SideStats
from manager_core.tactics.model import Tactic, default_tactic

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
SUBJECT, OPPONENTS = "ferroviario", ["mineracao", "pedra-branca", "rio-turvo", "uniao-operaria"]
N = 600


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def _base(provider: QuickSimProvider) -> Tactic:
    return default_tactic(provider.team_sheet(SUBJECT).formation.name)


def _team(tactic: Tactic, **settings: str) -> Tactic:
    team = dict(tactic.team)
    team.update(settings)
    return dataclasses.replace(tactic, team=tuple(sorted(team.items())))


def _play(provider: QuickSimProvider, tactic: Tactic | None) -> dict[str, float]:
    """Per-match averages for the subject ('for') and its opponents ('against')."""
    totals = dict.fromkeys(("shots", "shots_against", "xg", "xg_against", "fouls", "yellows",
                            "corners", "possession"), 0.0)
    me = provider.team_sheet(SUBJECT)
    for n in range(N):
        other = provider.team_sheet(OPPONENTS[n % len(OPPONENTS)])
        rng = random.Random(f"tactics:{n}")
        home = n % 2 == 0
        if home:
            _, report = simulate_match(me, other, provider.dataset.players, provider.params, rng,
                                       home_tactic=tactic)
            mine, theirs = report.home, report.away
        else:
            _, report = simulate_match(other, me, provider.dataset.players, provider.params, rng,
                                       away_tactic=tactic)
            mine, theirs = report.away, report.home
        _add(totals, mine, theirs)
    return {k: v / N for k, v in totals.items()}


def _add(totals: dict[str, float], mine: SideStats, theirs: SideStats) -> None:
    totals["shots"] += mine.shots
    totals["shots_against"] += theirs.shots
    totals["xg"] += mine.xg
    totals["xg_against"] += theirs.xg
    totals["fouls"] += mine.fouls
    totals["yellows"] += mine.yellows
    totals["corners"] += mine.corners
    totals["possession"] += mine.possession


@pytest.fixture(scope="module")
def baseline(provider: QuickSimProvider) -> dict[str, float]:
    return _play(provider, None)


def test_default_tactic_is_the_baseline(provider: QuickSimProvider,
                                        baseline: dict[str, float]) -> None:
    assert _play(provider, _base(provider)) == baseline


def test_attacking_mentality_opens_the_game(provider: QuickSimProvider,
                                            baseline: dict[str, float]) -> None:
    attacking = _play(provider, dataclasses.replace(_base(provider), mentality="very_attacking"))
    assert attacking["shots"] > baseline["shots"] * 1.08
    assert attacking["shots_against"] > baseline["shots_against"] * 1.05
    assert attacking["possession"] > baseline["possession"]


def test_defensive_mentality_closes_it(provider: QuickSimProvider,
                                       baseline: dict[str, float]) -> None:
    defensive = _play(provider, dataclasses.replace(_base(provider), mentality="very_defensive"))
    assert defensive["shots"] < baseline["shots"] * 0.92
    assert defensive["shots_against"] < baseline["shots_against"] * 0.95


def test_aggressive_tackling_costs_fouls_and_cards(provider: QuickSimProvider,
                                                   baseline: dict[str, float]) -> None:
    aggressive = _play(provider, _team(_base(provider), tackling="aggressive"))
    assert aggressive["fouls"] > baseline["fouls"] * 1.06
    assert aggressive["yellows"] > baseline["yellows"] * 1.08
    assert aggressive["shots_against"] < baseline["shots_against"]


def test_short_passing_keeps_the_ball(provider: QuickSimProvider,
                                      baseline: dict[str, float]) -> None:
    short = _play(provider, _team(_base(provider), passing_directness="much_shorter"))
    assert short["possession"] >= baseline["possession"] + 1.5


def test_wide_play_wins_corners(provider: QuickSimProvider,
                                baseline: dict[str, float]) -> None:
    wide = _play(provider, _team(_base(provider), attacking_width="much_wider"))
    assert wide["corners"] > baseline["corners"] * 1.03


def test_high_press_gives_up_better_chances(provider: QuickSimProvider,
                                            baseline: dict[str, float]) -> None:
    press = _play(provider, _team(_base(provider), line_of_engagement="high_press"))
    assert press["shots_against"] < baseline["shots_against"]
    assert (press["xg_against"] / press["shots_against"]
            > baseline["xg_against"] / baseline["shots_against"])


def test_reports_record_both_tactics(provider: QuickSimProvider) -> None:
    me = provider.team_sheet(SUBJECT)
    other = provider.team_sheet(OPPONENTS[0])
    tactic = dataclasses.replace(_base(provider), mentality="positive", style="possession")
    _, report = simulate_match(me, other, provider.dataset.players, provider.params,
                               random.Random("summary"), home_tactic=tactic)
    assert report.home_tactic is not None and report.away_tactic is not None
    assert report.home_tactic.mentality == "positive"
    assert report.home_tactic.style == "possession"
    assert report.away_tactic.mentality == "balanced"
    assert report.home_tactic.digest != report.away_tactic.digest


def test_a_stale_formation_falls_back_to_default_roles(provider: QuickSimProvider) -> None:
    me = provider.team_sheet(SUBJECT)
    other_formation = "3-5-2" if me.formation.name != "3-5-2" else "4-4-2"
    stale = dataclasses.replace(default_tactic(other_formation), mentality="attacking")
    _, report = simulate_match(me, provider.team_sheet(OPPONENTS[0]), provider.dataset.players,
                               provider.params, random.Random("stale"), home_tactic=stale)
    assert report.home_tactic is not None
    assert report.home_tactic.ip_formation == me.formation.name
    assert report.home_tactic.mentality == "attacking"
