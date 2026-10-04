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
from manager_core.tactics import ai
from manager_core.tactics.model import Tactic

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

    def __init__(self, dataset: Dataset, params: ModelParams | None = None,
                 ai_styles: bool = True) -> None:
        self.dataset = dataset
        self.params = params or load_params()
        self.ai_styles = ai_styles  # False: every club plays the default tactic (003's world)
        self._sheets = _sheets_for(dataset)
        self._overrides: dict[str, TeamSheet] = {}
        self._tactics: dict[str, Tactic] = {}
        self._styles: dict[str, str] | None = None

    def with_params(self, params: ModelParams) -> QuickSimProvider:
        """A provider with other parameters that shares this one's team sheets and styles."""
        twin = QuickSimProvider(self.dataset, params, self.ai_styles)
        twin._sheets = self._sheets
        twin._styles = self._styles
        twin._tactics = dict(self._tactics)
        return twin

    def set_tactic(self, club_id: str, tactic: Tactic | None) -> None:
        """Play this club with a fixed tactic (the user's, spec 006); None clears it."""
        if tactic is None:
            self._tactics.pop(club_id, None)
        else:
            self._tactics[club_id] = tactic

    def styles(self) -> dict[str, str]:
        """Each club's AI style, from the squads' best sheets (computed once)."""
        if self._styles is None:
            profiles = {cid: ai.squad_profile(self.team_sheet(cid), self.dataset.players,
                                              club.reputation)
                        for cid, club in sorted(self.dataset.clubs.items())}
            self._styles = ai.assign_styles(profiles)
        return self._styles

    def tactics_for(self, home: TeamSheet, away: TeamSheet
                    ) -> tuple[Tactic | None, Tactic | None]:
        """Both sides' tactics: the user's if set, else the AI style adapted to the match."""
        players = self.dataset.players
        strengths = (ai.strength(home, players), ai.strength(away, players))
        out: list[Tactic | None] = []
        for k, sheet in enumerate((home, away)):
            if sheet.club_id in self._tactics:
                out.append(self._tactics[sheet.club_id])
            elif not self.ai_styles or sheet.club_id not in self.dataset.clubs:
                out.append(None)
            else:
                style = self.styles()[sheet.club_id]
                tactic = ai.style_tactic(style, sheet.formation.name)
                out.append(ai.pre_match(tactic, strengths[k], strengths[1 - k], home=k == 0))
        return out[0], out[1]

    def override(self, club_id: str, sheet: TeamSheet | None) -> None:
        """Play this club with a fixed sheet (the user's selection, spec 005); None clears it."""
        if sheet is None:
            self._overrides.pop(club_id, None)
        else:
            self._overrides[club_id] = sheet

    def team_sheet(self, club_id: str, unavailable: frozenset[str] = frozenset()) -> TeamSheet:
        """The club's sheet without its unavailable (suspended) players, cached per set."""
        if club_id in self._overrides:  # the user's selection, repaired if someone is missing
            chosen = self._overrides[club_id]
            missing = unavailable & ({pid for _, pid in chosen.starters} | set(chosen.bench))
            if not missing:
                return chosen
            squad = sorted(self.dataset.squad(club_id), key=lambda p: p.id)
            return repair_team_sheet(chosen, squad,
                                     frozenset(unavailable & {p.id for p in squad}))
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
        home_sheet, away_sheet = self.team_sheet(home.id, out), self.team_sheet(away.id, out)
        home_tactic, away_tactic = self.tactics_for(home_sheet, away_sheet)
        result, _ = simulate_match(home_sheet, away_sheet, self.dataset.players, self.params, rng,
                                   context.neutral, home_tactic, away_tactic)
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
