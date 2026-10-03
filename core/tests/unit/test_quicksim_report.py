"""The match report model and its invariants (data-model.md, SC-005)."""

import dataclasses

import pytest

from manager_core.competition.results import Result
from manager_core.domain.positions import Position
from manager_core.quicksim.report import (
    AWAY,
    HOME,
    MatchEvent,
    MatchReport,
    Minute,
    SideLineup,
    SideStats,
    check_invariants,
)

H = [f"h{i}" for i in range(11)]
A = [f"a{i}" for i in range(11)]
SLOTS = [Position.GK] + [Position.DC] * 4 + [Position.MC] * 4 + [Position.ST] * 2


def _stats(goals: int = 0, sot: int = 0, shots: int = 0, possession: int = 50,
           yellows: int = 0, reds: int = 0) -> SideStats:
    return SideStats(goals, shots, sot, 0.0, possession, 0, 0, yellows, reds)


def _report(events: list[MatchEvent], home: SideStats | None = None,
            away: SideStats | None = None,
            home_finishers: list[str] | None = None) -> MatchReport:
    return MatchReport(
        home=home or _stats(), away=away or _stats(), events=tuple(events),
        home_lineup=SideLineup("h", "4-4-2", tuple(zip(SLOTS, H, strict=True)), ("hb1", "hb2")),
        away_lineup=SideLineup("a", "4-4-2", tuple(zip(SLOTS, A, strict=True)), ("ab1",)),
        home_finishers=tuple(home_finishers if home_finishers is not None else H),
        away_finishers=tuple(A), stoppage=(2, 5), model_version="test",
    )


def test_minute_format_and_order() -> None:
    assert str(Minute(90, 4)) == "90+4" and str(Minute(37)) == "37"
    assert Minute(45, 2) < Minute(46) < Minute(90) < Minute(90, 1)


def test_consistent_report_has_no_problems() -> None:
    events = [MatchEvent(Minute(10), HOME, "goal", "h10", "h9", 0.3),
              MatchEvent(Minute(20), AWAY, "yellow", "a2")]
    report = _report(events, home=_stats(1, 2, 5, 55), away=_stats(possession=45, yellows=1))
    result = Result(1, 0, "quick_sim", 0, 0, 0, 1)
    assert check_invariants(report, result) == []


VIOLATIONS = [
    ([MatchEvent(Minute(10), HOME, "goal", "h10")], _stats(1, 0, 3, 50), _stats(),
     "shot_counts:home"),
    ([], _stats(possession=60), _stats(possession=50), "possession"),
    ([MatchEvent(Minute(10), HOME, "yellow", "a1")], _stats(yellows=1), _stats(),
     "not_on_pitch:yellow:a1"),
    ([MatchEvent(Minute(10), HOME, "yellow", "h1"), MatchEvent(Minute(20), HOME, "yellow", "h1")],
     _stats(yellows=2), _stats(), "yellow_without_dismissal:h1"),
    ([MatchEvent(Minute(10), HOME, "red", "h1"), MatchEvent(Minute(20), HOME, "yellow", "h1")],
     _stats(yellows=1, reds=1), _stats(), "not_on_pitch:yellow:h1"),
    ([MatchEvent(Minute(10), HOME, "yellow", "h1")], _stats(), _stats(), "card_totals:home"),
]


@pytest.mark.parametrize(("events", "home", "away", "problem"), VIOLATIONS)
def test_violations(events: list[MatchEvent], home: SideStats, away: SideStats,
                    problem: str) -> None:
    finishers = [p for p in H if not any(e.kind == "red" and e.player_id == p for e in events)]
    assert problem in check_invariants(_report(events, home, away, finishers))


def _subs(pairs: list[tuple[int, str, str]]) -> list[MatchEvent]:
    return [MatchEvent(Minute(m), HOME, "sub", out, inn) for m, out, inn in pairs]


def test_more_than_five_subs_and_three_windows() -> None:
    bench = tuple(f"hb{i}" for i in range(1, 7))
    events = _subs([(60 + i, H[i + 1], bench[i]) for i in range(6)])
    lineup = SideLineup("h", "4-4-2", tuple(zip(SLOTS, H, strict=True)), bench)
    finishers = [p for p in H if p not in H[1:7]] + list(bench)
    report = dataclasses.replace(_report(events, home_finishers=finishers), home_lineup=lineup)
    problems = check_invariants(report)
    assert "too_many_subs:home" in problems
    assert "too_many_windows:home" in problems


def test_returning_player_is_rejected() -> None:
    events = _subs([(60, "h9", "hb1"), (70, "hb1", "h9")])
    assert "bad_sub:h9" in check_invariants(_report(events))


def test_result_must_match_report() -> None:
    report = _report([MatchEvent(Minute(10), HOME, "goal", "h10")], home=_stats(1, 1, 1, 50))
    assert "result_goals" in check_invariants(report, Result(2, 0, "quick_sim", 0, 0, 0, 0))
    assert "result_cards" in check_invariants(report, Result(1, 0, "quick_sim", 0, 0, 1, 0))
