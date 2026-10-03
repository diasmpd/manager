"""Knockout rounds (FR-004, FR-017): entrants, pairing, leg hosting and tie resolution."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from manager_core.competition.results import Result
from manager_core.competition.rules import Scoring, TieRule

PENALTIES_REQUIRED = "penalties_required"


@dataclass(frozen=True, slots=True)
class Tie:
    id: str
    stage_id: str
    track: str
    high_id: str  # better first-phase campaign
    low_id: str


@dataclass(frozen=True, slots=True)
class TieOutcome:
    winner_id: str | None  # None while penalties are still required
    decided_by: str  # aggregate / penalties / points / campaign / penalties_required


def overall_places(order: Sequence[str], places: tuple[int, int],
                   excluded: set[str]) -> list[str]:
    """Clubs from `places` in the overall classification; excluded clubs (entrants of other
    tracks) are skipped and the next places fill in."""
    wanted = places[1] - places[0] + 1
    eligible = [c for c in order[places[0] - 1:] if c not in excluded]
    return eligible[:wanted]


def pair(entrants_by_campaign: Sequence[str]) -> list[tuple[str, str]]:
    """Best campaign against worst: 1v4, 2v3 (also 1v2 for two entrants)."""
    n = len(entrants_by_campaign)
    return [(entrants_by_campaign[i], entrants_by_campaign[n - 1 - i]) for i in range(n // 2)]


def leg_hosts(tie: Tie, legs: int) -> list[tuple[str, str]]:
    """(home, away) per leg; the better campaign hosts the deciding (last) leg."""
    if legs == 1:
        return [(tie.high_id, tie.low_id)]
    return [(tie.low_id, tie.high_id), (tie.high_id, tie.low_id)]


def resolve_tie(tie: Tie, played: Sequence[tuple[str, str, Result]], rule: TieRule,
                scoring: Scoring) -> TieOutcome:
    if not 1 <= len(played) <= 2:
        raise ValueError(f"a tie has 1 or 2 legs, got {len(played)}")
    goals = {tie.high_id: 0, tie.low_id: 0}
    points = {tie.high_id: 0, tie.low_id: 0}
    for home, away, r in played:
        goals[home] += r.home_goals
        goals[away] += r.away_goals
        if r.home_goals > r.away_goals:
            points[home] += scoring.win
            points[away] += scoring.loss
        elif r.home_goals < r.away_goals:
            points[away] += scoring.win
            points[home] += scoring.loss
        else:
            points[home] += scoring.draw
            points[away] += scoring.draw

    if rule is TieRule.POINTS_THEN_CAMPAIGN:
        if points[tie.high_id] != points[tie.low_id]:
            return TieOutcome(max(points, key=lambda c: points[c]), "points")
        return TieOutcome(tie.high_id, "campaign")

    if goals[tie.high_id] != goals[tie.low_id]:
        return TieOutcome(max(goals, key=lambda c: goals[c]), "aggregate")
    shootout = played[-1][2].shootout
    if shootout is None:
        return TieOutcome(None, PENALTIES_REQUIRED)
    return TieOutcome(shootout.winner_id, "penalties")
