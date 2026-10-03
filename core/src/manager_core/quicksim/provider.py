"""`QuickSimProvider`: the quick sim behind 002's `ResultProvider` protocol (FR-001)."""

from __future__ import annotations

import random

from manager_core.competition.results import MatchContext, Result, Shootout
from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.params import ModelParams, load_params
from manager_core.quicksim.report import keeper_at_end
from manager_core.quicksim.shootout import play_shootout
from manager_core.quicksim.squad import TeamSheet, build_team_sheet, repair_team_sheet

# Team sheets per dataset, shared by every provider built on the same dataset object: picking
# 001's exact best XI costs about 0.1 s per club. Keyed by identity; the entry keeps the dataset
# alive, so an id is never reused while cached. Bounded to the few most recent datasets.
_SHEET_CACHE: dict[int, tuple[Dataset, dict[str, TeamSheet]]] = {}
_SHEET_CACHE_SIZE = 4


def _sheets_for(dataset: Dataset) -> dict[str, TeamSheet]:
    entry = _SHEET_CACHE.get(id(dataset))
    if entry is not None and entry[0] is dataset:
        return entry[1]
    while len(_SHEET_CACHE) >= _SHEET_CACHE_SIZE:
        del _SHEET_CACHE[next(iter(_SHEET_CACHE))]
    sheets: dict[str, TeamSheet] = {}
    _SHEET_CACHE[id(dataset)] = (dataset, sheets)
    return sheets


class QuickSimProvider:
    """Results from the quick sim. Team sheets are cached per club for the provider's lifetime
    (squads do not change in Milestone 0; spec 004 will invalidate the cache)."""

    def __init__(self, dataset: Dataset, params: ModelParams | None = None) -> None:
        self.dataset = dataset
        self.params = params or load_params()
        self._sheets = _sheets_for(dataset)

    def with_params(self, params: ModelParams) -> QuickSimProvider:
        """A provider with other parameters that shares this one's team sheets."""
        twin = QuickSimProvider(self.dataset, params)
        twin._sheets = self._sheets
        return twin

    def team_sheet(self, club_id: str, unavailable: frozenset[str] = frozenset()) -> TeamSheet:
        """The club's sheet without its unavailable (suspended) players, cached per set."""
        if club_id not in self._sheets:
            squad = sorted(self.dataset.squad(club_id), key=lambda p: p.id)
            self._sheets[club_id] = build_team_sheet(club_id, squad)
        base = self._sheets[club_id]
        if not unavailable & ({pid for _, pid in base.starters} | set(base.bench)):
            return base  # nobody in the sheet is missing
        squad = sorted(self.dataset.squad(club_id), key=lambda p: p.id)
        out = frozenset(unavailable & {p.id for p in squad})  # replacements exclude all of them
        key = f"{club_id}|{','.join(sorted(out))}"
        if key not in self._sheets:
            self._sheets[key] = repair_team_sheet(base, squad, out)
        return self._sheets[key]

    def play(self, match_id: str, home: Club, away: Club, context: MatchContext,
             rng: random.Random) -> Result:
        out = context.unavailable
        result, _ = simulate_match(self.team_sheet(home.id, out), self.team_sheet(away.id, out),
                                   self.dataset.players, self.params, rng, context.neutral)
        return result

    def shootout(self, match_id: str, first: Club, second: Club, context: MatchContext,
                 rng: random.Random, *, last_result: Result | None = None) -> Shootout:
        """`first` is the home side of the last leg; the kickers are its finishers."""
        report = last_result.report if last_result is not None else None
        sides = []
        for club, side in ((first, "home"), (second, "away")):
            if report is not None:
                ids = report.finishers(side)
                keeper_id = keeper_at_end(report, side)
            else:
                sheet = self.team_sheet(club.id)
                ids = tuple(pid for _, pid in sheet.starters)
                keeper_id = next((pid for i, pid in sheet.starters
                                  if sheet.slot_position(i) is Position.GK), None)
            players = [self.dataset.player(pid) for pid in sorted(ids)]
            keeper = self.dataset.player(keeper_id) if keeper_id else None
            sides.append((club.id, players, keeper))
        (a_id, a_players, a_keeper), (b_id, b_players, b_keeper) = sides
        return play_shootout(a_id, a_players, a_keeper, b_id, b_players, b_keeper,
                             self.params, rng)
