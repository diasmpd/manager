"""The SC-003 check (spec 011, owner decision 2026-10-18): do the synthesised squads win the
Mineiro as often as the real clubs do? Many seasons are simulated with the quick sim, and each
club's share of titles is set against the real list of champions over recent years. One real
season is too few games to rank clubs by (the game's own strength ranking matches a simulated
first phase at Spearman 0.7 only one season in five), so a title share is the target, and the last
real table is reported beside it for reference.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from manager_core import api
from manager_core.domain.dataset import Dataset
from manager_core.ratings.ability import current_ability

YEAR = 2027  # any year the ruleset's calendar covers
SEED = 7000


@dataclass(frozen=True, slots=True)
class StrengthCheck:
    seasons: int
    titles: dict[str, int]  # club -> simulated titles
    history: dict[str, int]  # club -> real titles in the reference years
    goals_per_match: float  # first-phase games
    strength: dict[str, float]  # club -> mean CA of its best 16

    def share(self, clubs: tuple[str, ...]) -> float:
        return sum(self.titles.get(c, 0) for c in clubs) / self.seasons

    def real_share(self, clubs: tuple[str, ...]) -> float:
        years = sum(self.history.values())
        return sum(self.history.get(c, 0) for c in clubs) / years if years else 0.0


def strength(dataset: Dataset, club_id: str, size: int = 16) -> float:
    """The mean CA of the club's best `size` players."""
    cas = sorted((current_ability(dataset.players[m.player_id])
                  for m in dataset.memberships.values() if m.club_id == club_id), reverse=True)
    top = cas[:size]
    return sum(top) / len(top) if top else 0.0


def spearman(a: list[str], b: list[str]) -> float:
    """Rank correlation of two orderings of the same clubs."""
    ra = {c: i for i, c in enumerate(a)}
    rb = {c: i for i, c in enumerate(b)}
    n = len(a)
    return 1 - 6 * sum((ra[c] - rb[c]) ** 2 for c in a) / (n * (n * n - 1))


def check(dataset: Dataset, seasons: int, history: dict[str, int],
          ruleset_id: str = api.DEFAULT_RULESET) -> StrengthCheck:
    titles: Counter[str] = Counter()
    goals = games = 0
    for i in range(seasons):
        season = api.start_season(dataset, ruleset_id, YEAR, SEED + i)
        season.advance_to(date(YEAR, 12, 31))
        outcome = season.outcome()
        if outcome is not None:
            titles[outcome.champion] += 1
        for match in season.group_matches():
            goals += match.result.home_goals + match.result.away_goals
            games += 1
    return StrengthCheck(seasons, dict(titles), dict(history), goals / games if games else 0.0,
                         {c: strength(dataset, c) for c in dataset.clubs})
