"""The positional engine's invariants (spec 008 T005, T006): a match completes, its report is a
valid quick-sim report, the same seed gives the same match, and the record covers it."""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.positional.engine import Decision, LiveMatch, simulate_positional
from manager_core.positional.params import load_params
from manager_core.positional.record import PositionalRecord
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import GOAL_KINDS

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset, ai_styles=False)


def _match(provider: QuickSimProvider, seed: int, record: bool = False) -> LiveMatch:
    home, away = provider.team_sheet("mineracao"), provider.team_sheet("rio-turvo")
    _, match = simulate_positional(
        home,
        away,
        provider.dataset.players,
        load_params(),
        provider.params,
        random.Random(seed),
        record=record,
    )
    return match


def test_a_match_completes_with_a_valid_report(provider: QuickSimProvider) -> None:
    match = _match(provider, 1)
    report = match.report()
    assert match.finished
    goals = sum(1 for e in report.events if e.kind in GOAL_KINDS)
    assert goals == report.home.goals + report.away.goals
    assert report.home.possession + report.away.possession == 100
    for side, stats in (("home", report.home), ("away", report.away)):
        assert (
            stats.shots
            >= stats.shots_on_target
            >= stats.goals
            - sum(1 for e in report.events if e.kind == "own_goal" and e.side == side)
        )
    assert len(report.home_finishers) <= 11 and len(report.away_finishers) <= 11
    assert all(e.minute.base <= 90 for e in report.events)
    assert match.result().source == "positional"


def test_the_same_seed_gives_the_same_match(provider: QuickSimProvider) -> None:
    a, b = _match(provider, 7), _match(provider, 7)
    assert a.report() == b.report()
    assert _match(provider, 8).report() != a.report()


def test_the_record_covers_the_match(provider: QuickSimProvider) -> None:
    match = _match(provider, 3, record=True)
    record = match.record()
    assert record.hz == 2
    minutes = match.t / 60
    assert len(record.samples) == pytest.approx(minutes * 60 * record.hz, rel=0.02)
    assert len(record.players) == 22
    assert all(index < len(record.samples) for index, _ in record.events)
    assert len(record.events) == len(match.events)
    assert PositionalRecord.decode(record.encode()) == record


def test_a_substitution_decision_is_applied_at_its_moment(provider: QuickSimProvider) -> None:
    home, away = provider.team_sheet("mineracao"), provider.team_sheet("rio-turvo")
    match = LiveMatch(
        home, away, provider.dataset.players, load_params(), provider.params, random.Random(5)
    )
    while match.half == 1 or match.minute().base < 60:  # to minute 60 (stoppage included)
        match.advance(30)
    team = match.teams["home"]
    off = next(b.pid for b in team.on_pitch() if b.slot == 9)
    on = team.bench[0]
    match.apply(Decision(match.t, "home", "substitution", off=off, on=on))
    match.play()
    subs = [e for e in match.events if e.kind == "sub" and e.player_id == off]
    assert subs and subs[0].other_player_id == on and 59 <= subs[0].minute.base <= 62
    # the same seed and decision replay the same match
    again = LiveMatch(
        home, away, provider.dataset.players, load_params(), provider.params, random.Random(5)
    )
    while again.half == 1 or again.minute().base < 60:
        again.advance(30)
    again.apply(Decision(again.t, "home", "substitution", off=off, on=on))
    again.play()
    assert again.report() == match.report()
