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


@dataclass(frozen=True, slots=True)
class LeagueFixture:
    season: int
    seed: int  # the season's seed: the match's context and the root of its random stream
    match_id: str
    home_id: str
    away_id: str

    def rng(self) -> random.Random:
        return random.Random(sub_seed(self.seed, f"match:{self.match_id}"))


def league_fixtures(dataset: Dataset, seasons: int) -> list[LeagueFixture]:
    """The league sample's matches in playing order. Both engines play this list (spec 008)."""
    clubs = tuple(sorted(dataset.clubs))
    fixtures: list[LeagueFixture] = []
    for n in range(seasons):
        seed = sub_seed(SEED, f"calibration:league:{n}")
        days = build_group_fixtures([Group("A", clubs)], Matching.ALL, 2, seed)
        for day_index, day in enumerate(days, start=1):
            for home, away in sorted(day):
                match_id = f"league-{n}-r{day_index:02d}-{home}-{away}"
                fixtures.append(LeagueFixture(n, seed, match_id, home, away))
    return fixtures


def league_sample(dataset: Dataset, provider: ResultProvider,
                  seasons: int) -> list[LeagueMatch]:
    matches: list[LeagueMatch] = []
    for f in league_fixtures(dataset, seasons):
        result = provider.play(f.match_id, dataset.club(f.home_id), dataset.club(f.away_id),
                               MatchContext(f.seed, "league"), f.rng())
        matches.append(LeagueMatch(f.season, f.home_id, f.away_id, result))
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
