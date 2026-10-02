"""Knockout entrants, pairing, hosting and tie resolution (FR-004, FR-017)."""

import dataclasses

import pytest

from manager_core.competition.knockout import (
    Tie,
    leg_hosts,
    overall_places,
    pair,
    resolve_tie,
)
from manager_core.competition.results import Result, Shootout
from manager_core.competition.rules import TieRule, load_ruleset

SCORING = load_ruleset("mg-modulo-i-2026").scoring
ORDER = [f"c{i:02d}" for i in range(1, 13)]  # overall classification, 1st..12th


def test_overall_places_without_exclusion() -> None:
    assert overall_places(ORDER, (5, 8), excluded=set()) == ["c05", "c06", "c07", "c08"]


def test_overall_places_skips_semifinalists() -> None:
    # Review regression: semifinalists ranked 6th and 7th are skipped; next places fill in.
    assert overall_places(ORDER, (5, 8), excluded={"c06", "c07"}) == ["c05", "c08", "c09", "c10"]


def test_pairing_best_vs_worst() -> None:
    assert pair(["a", "b", "c", "d"]) == [("a", "d"), ("b", "c")]
    assert pair(["x", "y"]) == [("x", "y")]


def test_better_campaign_hosts_second_leg() -> None:
    tie = Tie("t1", "semifinal", "main", "high", "low")
    assert leg_hosts(tie, legs=2) == [("low", "high"), ("high", "low")]
    assert leg_hosts(tie, legs=1) == [("high", "low")]


def _legs(*scores: tuple[int, int]) -> list[tuple[str, str, Result]]:
    hosts = [("low", "high"), ("high", "low")]
    return [(h, a, Result(g1, g2, "test")) for (h, a), (g1, g2) in zip(hosts, scores, strict=False)]


TIE = Tie("t1", "semifinal", "main", "high", "low")


def test_level_aggregate_is_detected() -> None:
    # leg 1: low 2 x 1 high; leg 2: high 1 x 0 low -> 2-2 on aggregate
    outcome = resolve_tie(TIE, _legs((2, 1), (1, 0)), TieRule.PENALTIES, SCORING)
    assert outcome.decided_by == "penalties_required"


def test_aggregate_winner() -> None:
    outcome = resolve_tie(TIE, _legs((0, 1), (2, 0)), TieRule.PENALTIES, SCORING)
    assert (outcome.winner_id, outcome.decided_by) == ("high", "aggregate")


def test_level_aggregate_goes_to_penalties_no_away_goals() -> None:
    legs = _legs((1, 1), (0, 0))  # 1-1 on aggregate, away goal for 'high' does not count
    pending = resolve_tie(TIE, legs, TieRule.PENALTIES, SCORING)
    assert pending.decided_by == "penalties_required"
    kicks = (("high", True), ("low", False), ("high", True), ("low", False), ("high", True),
             ("low", False))
    h, a, r = legs[-1]
    legs[-1] = (h, a, dataclasses.replace(r, shootout=Shootout(kicks, "high")))
    outcome = resolve_tie(TIE, legs, TieRule.PENALTIES, SCORING)
    assert (outcome.winner_id, outcome.decided_by) == ("high", "penalties")


def test_points_then_campaign() -> None:
    # 2-0 for low, then 1-0 for high: 3 points each -> better campaign (high) advances,
    # even though low leads on aggregate. No shootout.
    outcome = resolve_tie(TIE, _legs((2, 0), (1, 0)), TieRule.POINTS_THEN_CAMPAIGN, SCORING)
    assert (outcome.winner_id, outcome.decided_by) == ("high", "campaign")
    outcome = resolve_tie(TIE, _legs((1, 0), (1, 1)), TieRule.POINTS_THEN_CAMPAIGN, SCORING)
    assert (outcome.winner_id, outcome.decided_by) == ("low", "points")


def test_single_match_draw_needs_penalties() -> None:
    legs = [("high", "low", Result(0, 0, "test"))]
    assert resolve_tie(TIE, legs, TieRule.PENALTIES, SCORING).decided_by == "penalties_required"


@pytest.mark.parametrize("bad", [[], [("high", "low", Result(0, 0, "test"))] * 3])
def test_wrong_number_of_legs(bad: list[tuple[str, str, Result]]) -> None:
    with pytest.raises(ValueError):
        resolve_tie(TIE, bad, TieRule.PENALTIES, SCORING)
