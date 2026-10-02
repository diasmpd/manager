"""Season engine (research R10).

`Season.start` validates the request, draws the groups, builds and dates the group-stage
fixtures and reserves the knockout date slots. Every random decision uses its own sub-seed, so
a season is fully determined by (ruleset, year, master seed, participants, result provider).
Playing the season day by day (`advance_to`) is added by US2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from manager_core.competition.draw import Group, draw_groups
from manager_core.competition.fixtures import build_group_fixtures
from manager_core.competition.results import PlaceholderProvider, Result, ResultProvider
from manager_core.competition.rules import KnockoutStageRule, Ruleset
from manager_core.competition.scheduler import (
    SchedulingError,
    Slot,
    assign_kickoffs,
    next_weekend_after,
    plan_slots,
    resolve_window,
)
from manager_core.competition.seeds import season_seed, sub_seed
from manager_core.domain.dataset import Dataset
from manager_core.i18n import t


class SeasonError(Exception):
    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.message = t(f"season.{code}", **params)
        super().__init__(f"{code}: {self.message}")


@dataclass(frozen=True, slots=True)
class Match:
    id: str
    stage_id: str
    round: int  # matchday for group stages, leg for knockouts
    home_id: str
    away_id: str
    kickoff: datetime
    venue: str
    tie_id: str | None = None


@dataclass(frozen=True, slots=True)
class SeasonEvent:
    day: date
    kind: str
    payload: tuple[str, ...] = ()


@dataclass
class Season:
    dataset: Dataset
    ruleset: Ruleset
    year: int
    master_seed: int
    seed: int
    participants: tuple[str, ...]
    groups: tuple[Group, ...]
    provider: ResultProvider
    stage_slots: dict[str, list[Slot]]
    matches: dict[str, Match] = field(default_factory=dict)
    results: dict[str, Result] = field(default_factory=dict)
    events: list[SeasonEvent] = field(default_factory=list)
    current_date: date = date.min

    # ---- creation ------------------------------------------------------------------------

    @classmethod
    def start(cls, dataset: Dataset, ruleset: Ruleset, year: int, master_seed: int,
              participants: Sequence[str] | None = None,
              provider: ResultProvider | None = None) -> Season:
        if not ruleset.is_valid_for(year):
            valid = f"{ruleset.valid_from}–{ruleset.valid_to or ''}"
            raise SeasonError("S001", ruleset=ruleset.id, valid=valid, year=year)
        chosen = tuple(sorted(participants)) if participants is not None else tuple(sorted(
            c.id for c in dataset.clubs.values()
            if c.state == ruleset.state and c.country == ruleset.country
        ))
        if len(chosen) != ruleset.participants:
            raise SeasonError("S002", ruleset=ruleset.id, expected=ruleset.participants,
                              got=len(chosen))
        seed = season_seed(master_seed, year)
        group_rule = ruleset.group_stage
        clubs = [dataset.club(c) for c in chosen]
        groups = draw_groups(clubs, group_rule, sub_seed(seed, f"draw:{ruleset.id}"))
        matchdays = build_group_fixtures(groups, group_rule.matching, group_rule.rounds,
                                         sub_seed(seed, f"fixtures:{ruleset.id}"))
        stage_slots = _reserve_slots(ruleset, year, len(matchdays))
        season = cls(
            dataset=dataset, ruleset=ruleset, year=year, master_seed=master_seed, seed=seed,
            participants=chosen, groups=groups,
            provider=provider or PlaceholderProvider(dataset), stage_slots=stage_slots,
            current_date=date(year, 1, 1),
        )
        season._schedule_group_stage(matchdays)
        draw_day = resolve_window(ruleset.calendar, year)[0] - timedelta(days=7)
        season.events.append(SeasonEvent(draw_day, "draw", tuple(g.label for g in groups)))
        return season

    def _schedule_group_stage(self, matchdays: list[list[tuple[str, str]]]) -> None:
        stage_id = self.ruleset.group_stage.id
        last: dict[str, datetime] = {}
        for index, (day, slot) in enumerate(
                zip(matchdays, self.stage_slots[stage_id], strict=True), start=1):
            pairs = sorted(day)
            try:
                kickoffs = assign_kickoffs(pairs, slot, self.ruleset.calendar, last)
            except SchedulingError as exc:
                raise SeasonError("S003", stage=stage_id, detail=str(exc)) from exc
            for n, ((home, away), when) in enumerate(zip(pairs, kickoffs, strict=True), start=1):
                match_id = f"{stage_id}-r{index:02d}-{n:02d}"
                self.matches[match_id] = Match(match_id, stage_id, index, home, away, when,
                                               self.dataset.club(home).stadium_name)
                last[home] = last[away] = when

    # ---- views ---------------------------------------------------------------------------

    def club_name(self, club_id: str) -> str:
        return self.dataset.club(club_id).short_name

    def sorted_matches(self) -> list[Match]:
        return sorted(self.matches.values(), key=lambda m: (m.kickoff, m.id))


def _reserve_slots(ruleset: Ruleset, year: int, group_rounds: int) -> dict[str, list[Slot]]:
    """Main path = group rounds + every leg of the main-track knockouts, in order. Side tracks
    share the slots of the stage named in `dates_with`; extra legs take the next weekend."""
    cal = ruleset.calendar
    main = [s for s in ruleset.knockout_stages if s.track == "main"]
    main_rounds = group_rounds + sum(s.legs for s in main)
    try:
        slots = plan_slots(cal, year, main_rounds, group_rounds)
    except SchedulingError as exc:
        raise SeasonError("S003", stage=ruleset.group_stage.id, detail=str(exc)) from exc
    reserved: dict[str, list[Slot]] = {ruleset.group_stage.id: slots[:group_rounds]}
    cursor = group_rounds
    for stage in main:
        reserved[stage.id] = slots[cursor:cursor + stage.legs]
        cursor += stage.legs
    for stage in ruleset.knockout_stages:
        if stage.track == "main":
            continue
        reserved[stage.id] = _side_slots(stage, reserved, ruleset, year)
    return reserved


def _side_slots(stage: KnockoutStageRule, reserved: dict[str, list[Slot]], ruleset: Ruleset,
                year: int) -> list[Slot]:
    shared = list(reserved.get(stage.dates_with or "", []))[: stage.legs]
    while len(shared) < stage.legs:
        last_day = shared[-1].days[-1] if shared else resolve_window(ruleset.calendar, year)[1]
        nxt = next_weekend_after(ruleset.calendar, year, last_day)
        if not stage.may_exceed_window and nxt.days[-1] > date(year, *ruleset.calendar.window_end):
            raise SeasonError("S003", stage=stage.id, detail="no slot left in the window")
        shared.append(nxt)
    return shared
