"""Match results and the result-provider entry point (FR-016, research R9).

`PlaceholderProvider` is deliberately simple and NOT calibrated: it exists so the competition
engine can be built and tested before the real quick sim (spec 003) replaces it through the
`ResultProvider` protocol. Every result it produces is labelled `source="placeholder"`.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset
from manager_core.ratings.ability import current_ability, is_goalkeeper

if TYPE_CHECKING:  # the competition engine does not depend on the quick sim at runtime
    from manager_core.quicksim.report import MatchReport

PLACEHOLDER = "placeholder"
SHOOTOUT_ROUNDS = 5


@dataclass(frozen=True, slots=True)
class Shootout:
    """Kicks in order as (club_id, scored); alternating, first club kicks first."""

    kicks: tuple[tuple[str, bool], ...]
    winner_id: str

    def __post_init__(self) -> None:
        if len(self.kicks) < 2:
            raise ValueError("a shootout has at least one kick per side")
        first, second = self.kicks[0][0], self.kicks[1][0]
        goals = {first: 0, second: 0}
        taken = {first: 0, second: 0}
        decided_at: int | None = None
        for i, (club, scored) in enumerate(self.kicks):
            expected = first if i % 2 == 0 else second
            if club != expected:
                raise ValueError("kicks must alternate")
            taken[club] += 1
            goals[club] += int(scored)
            if decided_at is None and _decided(goals, taken, first, second):
                decided_at = i
        if decided_at is None or decided_at != len(self.kicks) - 1:
            raise ValueError("a shootout ends exactly when it is decided")
        leader = max(goals, key=lambda c: goals[c])
        if leader != self.winner_id:
            raise ValueError("winner does not match the kicks")

    @property
    def score(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for club, scored in self.kicks:
            result[club] = result.get(club, 0) + int(scored)
        return result


def _decided(goals: Mapping[str, int], taken: Mapping[str, int], first: str, second: str) -> bool:
    if taken[first] <= SHOOTOUT_ROUNDS and taken[second] <= SHOOTOUT_ROUNDS:
        left_first = SHOOTOUT_ROUNDS - taken[first]
        left_second = SHOOTOUT_ROUNDS - taken[second]
        return (goals[first] > goals[second] + left_second
                or goals[second] > goals[first] + left_first)
    # sudden death: decided after both have taken the same number of kicks
    return taken[first] == taken[second] and goals[first] != goals[second]


@dataclass(frozen=True, slots=True)
class Result:
    home_goals: int
    away_goals: int
    source: str
    home_red: int | None = None
    away_red: int | None = None
    home_yellow: int | None = None
    away_yellow: int | None = None
    shootout: Shootout | None = None
    report: MatchReport | None = None  # the quick sim's match report (spec 003)

    def __post_init__(self) -> None:
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")
        if not self.source:
            raise ValueError("a result must state its source")

    @property
    def has_cards(self) -> bool:
        return self.home_red is not None and self.home_yellow is not None


@dataclass(frozen=True, slots=True)
class MatchContext:
    season_seed: int
    stage_id: str
    neutral: bool = False  # no home advantage (e.g. a final at a neutral venue)


@runtime_checkable
class ResultProvider(Protocol):
    def play(self, match_id: str, home: Club, away: Club, context: MatchContext,
             rng: random.Random) -> Result: ...

    def shootout(self, match_id: str, first: Club, second: Club, context: MatchContext,
                 rng: random.Random, *, last_result: Result | None = None) -> Shootout: ...


class PlaceholderProvider:
    """Temporary results from team strength, home advantage and a per-match seeded RNG."""

    HOME_BASE = 1.30
    AWAY_BASE = 1.05
    STRENGTH_SLOPE = 0.020
    PENALTY_SCORE_PROBABILITY = 0.75

    def __init__(self, dataset: Dataset) -> None:
        self._dataset = dataset
        self._strength: dict[str, float] = {}

    def strength(self, club_id: str) -> float:
        """Mean CA of the 11 best players, at least one of them a goalkeeper."""
        if club_id not in self._strength:
            players = sorted(self._dataset.squad(club_id),
                             key=lambda p: (-current_ability(p), p.id))
            keepers = [p for p in players if is_goalkeeper(p)]
            chosen = keepers[:1] + [p for p in players if p not in keepers[:1]][:10]
            abilities = [current_ability(p) for p in chosen]
            self._strength[club_id] = sum(abilities) / len(abilities) if abilities else 0.0
        return self._strength[club_id]

    def play(self, match_id: str, home: Club, away: Club, context: MatchContext,
             rng: random.Random) -> Result:
        diff = self.strength(home.id) - self.strength(away.id)
        home_goals = _poisson(rng, self.HOME_BASE * math.exp(self.STRENGTH_SLOPE * diff))
        away_goals = _poisson(rng, self.AWAY_BASE * math.exp(-self.STRENGTH_SLOPE * diff))
        return Result(home_goals, away_goals, PLACEHOLDER)

    def shootout(self, match_id: str, first: Club, second: Club, context: MatchContext,
                 rng: random.Random, *, last_result: Result | None = None) -> Shootout:
        kicks: list[tuple[str, bool]] = []
        goals = {first.id: 0, second.id: 0}
        taken = {first.id: 0, second.id: 0}
        while True:
            for club in (first.id, second.id):
                scored = rng.random() < self.PENALTY_SCORE_PROBABILITY
                kicks.append((club, scored))
                taken[club] += 1
                goals[club] += int(scored)
                if _decided(goals, taken, first.id, second.id):
                    winner = max(goals, key=lambda c: goals[c])
                    return Shootout(tuple(kicks), winner)


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's method; fine for football-sized means."""
    limit = math.exp(-lam)
    k, product = 0, rng.random()
    while product > limit:
        k += 1
        product *= rng.random()
    return k
