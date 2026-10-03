"""Fixed calibration samples (research R10).

- **league**: the 12 sample clubs in a double round-robin (132 matches per season), built with
  002's fixture generator. Used for scorelines, cards, stats and favourites.
- **mineiro**: full Mineiro seasons through 002's season engine (first phase, knockouts and
  shootouts).

Every match draws its RNG from a fixed label, so a sample is a pure function of the dataset,
the parameters and the gate.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from manager_core.competition.draw import Group
from manager_core.competition.fixtures import build_group_fixtures
from manager_core.competition.results import MatchContext, Result, ResultProvider
from manager_core.competition.rules import Matching, load_ruleset
from manager_core.competition.season import Season
from manager_core.competition.seeds import sub_seed
from manager_core.domain.dataset import Dataset

SEED = 20261002
MINEIRO_RULESET = "mg-modulo-i-2026"
MINEIRO_YEAR = 2027


@dataclass(frozen=True, slots=True)
class SampleSpec:
    gate: str
    league_seasons: int
    mineiro_seasons: int


GATES = {
    "pr": SampleSpec("pr", league_seasons=20, mineiro_seasons=30),
    "milestone": SampleSpec("milestone", league_seasons=100, mineiro_seasons=300),
}


@dataclass(frozen=True, slots=True)
class LeagueMatch:
    season: int
    home_id: str
    away_id: str
    result: Result


def league_sample(dataset: Dataset, provider: ResultProvider,
                  seasons: int) -> list[LeagueMatch]:
    clubs = tuple(sorted(dataset.clubs))
    matches: list[LeagueMatch] = []
    for n in range(seasons):
        seed = sub_seed(SEED, f"calibration:league:{n}")
        days = build_group_fixtures([Group("A", clubs)], Matching.ALL, 2, seed)
        for day_index, day in enumerate(days, start=1):
            for home, away in sorted(day):
                match_id = f"league-{n}-r{day_index:02d}-{home}-{away}"
                rng = random.Random(sub_seed(seed, f"match:{match_id}"))
                result = provider.play(match_id, dataset.club(home), dataset.club(away),
                                       MatchContext(seed, "league"), rng)
                matches.append(LeagueMatch(n, home, away, result))
    return matches


def mineiro_sample(dataset: Dataset, provider: ResultProvider, seasons: int) -> list[Season]:
    ruleset = load_ruleset(MINEIRO_RULESET)
    played = []
    for n in range(seasons):
        master = sub_seed(SEED, f"calibration:mineiro:{n}") % 2**31
        season = Season.start(dataset, ruleset, MINEIRO_YEAR, master, provider=provider)
        season.advance_to(date(MINEIRO_YEAR, 12, 31))
        played.append(season)
    return played
