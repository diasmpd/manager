"""League tables with the ruleset's tiebreakers (FR-012..014, research R8).

Clubs are ordered by points, then each tied subset is split criterion by criterion; the
remaining criteria apply inside each sub-group. Every row records `decided_by`: the criterion
that separated it from the row below, so the owner can audit why a club is above another.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from manager_core.competition.results import Result
from manager_core.competition.rules import Scoring, Tiebreaker
from manager_core.competition.seeds import sub_seed

POINTS = "points"


@dataclass(frozen=True, slots=True)
class PlayedMatch:
    home_id: str
    away_id: str
    result: Result


@dataclass
class _Record:
    club_id: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    red: int | None = 0
    yellow: int | None = 0

    def points(self, scoring: Scoring) -> int:
        return self.won * scoring.win + self.drawn * scoring.draw + self.lost * scoring.loss


@dataclass(frozen=True, slots=True)
class TableRow:
    place: int
    club_id: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    red_cards: int | None
    yellow_cards: int | None
    decided_by: str | None  # criterion separating this row from the next one
    zone: str | None = None


def _add_cards(current: int | None, value: int | None) -> int | None:
    return None if current is None or value is None else current + value


def records(club_ids: Sequence[str], matches: Sequence[PlayedMatch]) -> dict[str, _Record]:
    recs = {c: _Record(c) for c in club_ids}
    for m in matches:
        r = m.result
        sides = ((m.home_id, r.home_goals, r.away_goals, r.home_red, r.home_yellow),
                 (m.away_id, r.away_goals, r.home_goals, r.away_red, r.away_yellow))
        for club, gf, ga, red, yellow in sides:
            if club not in recs:
                continue
            rec = recs[club]
            rec.played += 1
            rec.goals_for += gf
            rec.goals_against += ga
            rec.won += gf > ga
            rec.drawn += gf == ga
            rec.lost += gf < ga
            rec.red = _add_cards(rec.red, red)
            rec.yellow = _add_cards(rec.yellow, yellow)
    return recs


def _head_to_head(a: str, b: str, matches: Sequence[PlayedMatch],
                  scoring: Scoring) -> tuple[int, int] | None:
    """(points, goal difference) of `a` minus `b` in their mutual matches; None if never met."""
    mutual = [m for m in matches if {m.home_id, m.away_id} == {a, b}]
    if not mutual:
        return None
    mini = records([a, b], mutual)
    return (mini[a].points(scoring) - mini[b].points(scoring),
            (mini[a].goals_for - mini[a].goals_against)
            - (mini[b].goals_for - mini[b].goals_against))


def rank(club_ids: Sequence[str], recs: dict[str, _Record], matches: Sequence[PlayedMatch],
         scoring: Scoring, seed: int, label: str) -> list[tuple[str, str | None]]:
    """Ordered (club, decided_by) pairs; decided_by separates a club from the next one."""
    criteria: list[str] = [POINTS, *(t.value for t in scoring.tiebreakers)]

    def key_for(criterion: str) -> Callable[[str], object] | None:
        if criterion == POINTS:
            return lambda c: -recs[c].points(scoring)
        if criterion == Tiebreaker.WINS:
            return lambda c: -recs[c].won
        if criterion == Tiebreaker.GOAL_DIFFERENCE:
            return lambda c: -(recs[c].goals_for - recs[c].goals_against)
        if criterion == Tiebreaker.GOALS_FOR:
            return lambda c: -recs[c].goals_for
        if criterion == Tiebreaker.FEWER_RED_CARDS:
            return lambda c: recs[c].red
        if criterion == Tiebreaker.FEWER_YELLOW_CARDS:
            return lambda c: recs[c].yellow
        return None

    def split(group: list[str], index: int) -> list[tuple[str, str | None]]:
        if len(group) == 1:
            return [(group[0], None)]
        criterion = criteria[index]
        if criterion == Tiebreaker.DRAW:
            lots = sub_seed(seed, f"lots:{label}:{','.join(sorted(group))}")
            ordered = sorted(group)
            random.Random(lots).shuffle(ordered)
            return [(c, Tiebreaker.DRAW.value) for c in ordered[:-1]] + [(ordered[-1], None)]
        if criterion == Tiebreaker.HEAD_TO_HEAD:
            if len(group) == 2:
                diff = _head_to_head(group[0], group[1], matches, scoring)
                if diff is not None and diff != (0, 0):
                    first, second = (group if diff > (0, 0) else list(reversed(group)))
                    return [(first, criterion), (second, None)]
            return split(group, index + 1)
        key = key_for(criterion)
        assert key is not None
        values = {c: key(c) for c in group}
        if any(v is None for v in values.values()):  # missing card data: criterion is neutral
            return split(group, index + 1)
        buckets: dict[object, list[str]] = {}
        for c in sorted(group, key=lambda c: (values[c], c)):
            buckets.setdefault(values[c], []).append(c)
        if len(buckets) == 1:
            return split(group, index + 1)
        out: list[tuple[str, str | None]] = []
        for bucket in buckets.values():
            part = split(bucket, index + 1)
            if out:
                out[-1] = (out[-1][0], criterion)
            out.extend(part)
        return out

    return split(sorted(club_ids), 0)


def build_table(club_ids: Sequence[str], matches: Sequence[PlayedMatch], scoring: Scoring,
                seed: int, label: str) -> list[TableRow]:
    recs = records(club_ids, matches)
    ordered = rank(club_ids, recs, matches, scoring, seed, label)
    rows = []
    for place, (club, decided_by) in enumerate(ordered, start=1):
        r = recs[club]
        rows.append(TableRow(
            place=place, club_id=club, played=r.played, won=r.won, drawn=r.drawn, lost=r.lost,
            goals_for=r.goals_for, goals_against=r.goals_against,
            goal_difference=r.goals_for - r.goals_against, points=r.points(scoring),
            red_cards=r.red, yellow_cards=r.yellow, decided_by=decided_by,
        ))
    return rows
