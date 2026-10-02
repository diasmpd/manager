"""Season engine (research R10).

`Season.start` validates the request, draws the groups, builds and dates the group-stage
fixtures and reserves the knockout date slots. Every random decision uses its own sub-seed, so
a season is fully determined by (ruleset, year, master seed, participants, result provider).

`advance_to` plays day by day: each day's matches in kick-off order, then the stage
transitions (qualification, relegation, pairing and dating of knockout rounds, titles).
"""

from __future__ import annotations

import dataclasses
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from manager_core.competition.draw import Group, draw_groups
from manager_core.competition.fixtures import build_group_fixtures
from manager_core.competition.knockout import (
    PENALTIES_REQUIRED,
    Tie,
    TieOutcome,
    leg_hosts,
    overall_places,
    pair,
    resolve_tie,
)
from manager_core.competition.results import (
    MatchContext,
    PlaceholderProvider,
    Result,
    ResultProvider,
)
from manager_core.competition.rules import (
    EntrantKind,
    EntrantRule,
    KnockoutStageRule,
    Ruleset,
    Venue,
)
from manager_core.competition.scheduler import (
    SchedulingError,
    Slot,
    assign_kickoffs,
    next_weekend_after,
    plan_slots,
    resolve_window,
)
from manager_core.competition.seeds import season_seed, sub_seed
from manager_core.competition.standings import (
    PlayedMatch,
    TableRow,
    build_table,
    rank,
    records,
)
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


@dataclass(frozen=True, slots=True)
class Outcome:
    champion: str
    runner_up: str
    semifinalists: tuple[str, ...]
    side_entrants: dict[str, list[str]]
    side_titles: dict[str, str]
    relegated: list[str]
    final_classification: tuple[str, ...]


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
    ties: dict[str, Tie] = field(default_factory=dict)
    tie_matches: dict[str, list[str]] = field(default_factory=dict)
    tie_outcomes: dict[str, TieOutcome] = field(default_factory=dict)
    stage_entrants: dict[str, list[str]] = field(default_factory=dict)
    stages_done: set[str] = field(default_factory=set)
    overall: tuple[str, ...] = ()
    relegated: list[str] = field(default_factory=list)
    titles: dict[str, str] = field(default_factory=dict)  # track -> winner
    runner_up: str | None = None

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
            current_date=date(year, 1, 1) - timedelta(days=1),
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

    # ---- playing -------------------------------------------------------------------------

    def advance_to(self, day: date) -> list[SeasonEvent]:
        """Play every day after the current date up to and including `day`."""
        if day > date(self.year, 12, 31):
            raise SeasonError("S004", year=self.year)
        first_new = len(self.events)
        current = self.current_date
        while current < day:
            current += timedelta(days=1)
            self._play_day(current)
            self._transitions(current)
        self.current_date = max(self.current_date, day)
        return self.events[first_new:]

    def _play_day(self, day: date) -> None:
        todays = sorted((m for m in self.matches.values()
                         if m.kickoff.date() == day and m.id not in self.results),
                        key=lambda m: (m.kickoff, m.id))
        for m in todays:
            rng = random.Random(sub_seed(self.seed, f"match:{m.id}"))
            ctx = MatchContext(self.seed, m.stage_id)
            self.results[m.id] = self.provider.play(
                m.id, self.dataset.club(m.home_id), self.dataset.club(m.away_id), ctx, rng)
            if m.tie_id is not None:
                self._maybe_resolve_tie(m.tie_id)

    def _maybe_resolve_tie(self, tie_id: str) -> None:
        legs = self.tie_matches[tie_id]
        if not all(mid in self.results for mid in legs):
            return
        tie = self.ties[tie_id]
        stage = self.ruleset.stage(tie.stage_id)
        assert isinstance(stage, KnockoutStageRule)
        played = [(self.matches[mid].home_id, self.matches[mid].away_id, self.results[mid])
                  for mid in legs]
        outcome = resolve_tie(tie, played, stage.tie_rule, self.ruleset.scoring)
        if outcome.decided_by == PENALTIES_REQUIRED:
            last = legs[-1]
            rng = random.Random(sub_seed(self.seed, f"shootout:{tie_id}"))
            m = self.matches[last]
            shootout = self.provider.shootout(
                last, self.dataset.club(m.home_id), self.dataset.club(m.away_id),
                MatchContext(self.seed, tie.stage_id), rng)
            self.results[last] = dataclasses.replace(self.results[last], shootout=shootout)
            played[-1] = (played[-1][0], played[-1][1], self.results[last])
            outcome = resolve_tie(tie, played, stage.tie_rule, self.ruleset.scoring)
        self.tie_outcomes[tie_id] = outcome

    def _transitions(self, day: date) -> None:
        changed = True
        while changed:
            changed = False
            group_id = self.ruleset.group_stage.id
            if group_id not in self.stages_done and self._stage_complete(group_id):
                self._finish_group_stage(day)
                changed = True
            for stage in self.ruleset.knockout_stages:
                if stage.id not in self.stage_entrants and self._sources_done(stage):
                    self._create_knockout(stage, day)
                    changed = True
                elif (stage.id in self.stage_entrants and stage.id not in self.stages_done
                      and self._stage_complete(stage.id)):
                    self._finish_knockout(stage, day)
                    changed = True

    def _stage_complete(self, stage_id: str) -> bool:
        if stage_id == self.ruleset.group_stage.id:
            return all(m.id in self.results for m in self.matches.values()
                       if m.stage_id == stage_id)
        tie_ids = [t.id for t in self.ties.values() if t.stage_id == stage_id]
        return bool(tie_ids) and all(t in self.tie_outcomes for t in tie_ids)

    def _sources_done(self, stage: KnockoutStageRule) -> bool:
        return all(e.source in self.stages_done for e in stage.entrants)

    def group_matches(self) -> list[PlayedMatch]:
        gid = self.ruleset.group_stage.id
        return [PlayedMatch(m.home_id, m.away_id, self.results[m.id])
                for m in self.sorted_matches() if m.stage_id == gid and m.id in self.results]

    def overall_table(self) -> list[TableRow]:
        return build_table(self.participants, self.group_matches(), self.ruleset.scoring,
                           self.seed, f"{self.ruleset.id}:overall")

    def group_table(self, group_label: str) -> list[TableRow]:
        group = next(g for g in self.groups if g.label == group_label)
        return build_table(group.club_ids, self.group_matches(), self.ruleset.scoring,
                           self.seed, f"{self.ruleset.id}:group:{group_label}")

    def _finish_group_stage(self, day: date) -> None:
        rule = self.ruleset.group_stage
        self.stages_done.add(rule.id)
        self.overall = tuple(r.club_id for r in self.overall_table())
        self.events.append(SeasonEvent(day, "stage_complete", (rule.id,)))
        for outcome in rule.outcomes:
            self.relegated = list(self.overall[outcome.places[0] - 1:outcome.places[1]])
            self.events.append(SeasonEvent(day, "relegated", tuple(self.relegated)))

    def _campaign_order(self, clubs: Sequence[str]) -> list[str]:
        return sorted(clubs, key=self.overall.index)

    def _entrants(self, stage: KnockoutStageRule) -> list[str]:
        chosen: list[str] = []
        for rule in stage.entrants:
            chosen.extend(c for c in self._resolve_entrant(rule) if c not in chosen)
        return self._campaign_order(chosen)

    def _resolve_entrant(self, rule: EntrantRule) -> list[str]:
        if rule.kind is EntrantKind.GROUP_WINNERS:
            return [self.group_table(g.label)[0].club_id for g in self.groups]
        if rule.kind is EntrantKind.BEST_OF_PLACE:
            assert rule.place is not None and rule.count is not None
            candidates = [self.group_table(g.label)[rule.place - 1].club_id for g in self.groups]
            matches = self.group_matches()
            ordered = rank(candidates, records(candidates, matches), matches,
                           self.ruleset.scoring, self.seed,
                           f"{self.ruleset.id}:best-of-place-{rule.place}")
            return [c for c, _ in ordered][: rule.count]
        if rule.kind is EntrantKind.OVERALL_PLACES:
            assert rule.places is not None
            excluded = {c for s in self.ruleset.knockout_stages if s.track in rule.exclude_tracks
                        for c in self.stage_entrants.get(s.id, [])}
            return overall_places(self.overall, rule.places, excluded)
        return [o.winner_id for tid, o in sorted(self.tie_outcomes.items())
                if self.ties[tid].stage_id == rule.source and o.winner_id is not None]

    def _create_knockout(self, stage: KnockoutStageRule, day: date) -> None:
        entrants = self._entrants(stage)
        self.stage_entrants[stage.id] = entrants
        self.events.append(SeasonEvent(day, "qualified", (stage.id, *entrants)))
        slots = self.stage_slots[stage.id]
        neutral = self.ruleset.neutral_venue
        for n, (high, low) in enumerate(pair(entrants), start=1):
            tie = Tie(f"{stage.id}-t{n}", stage.id, stage.track, high, low)
            self.ties[tie.id] = tie
            self.tie_matches[tie.id] = []
            for leg, ((home, away), slot) in enumerate(
                    zip(leg_hosts(tie, stage.legs), slots, strict=True), start=1):
                last = self._last_kickoffs(slot.first_day, (home, away))
                try:
                    kickoff = assign_kickoffs([(home, away)], slot, self.ruleset.calendar, last)[0]
                except SchedulingError as exc:
                    raise SeasonError("S003", stage=stage.id, detail=str(exc)) from exc
                venue = (neutral.name if stage.venue is Venue.NEUTRAL and neutral
                         else self.dataset.club(home).stadium_name)
                match_id = f"{stage.id}-t{n}-l{leg}"
                self.matches[match_id] = Match(match_id, stage.id, leg, home, away, kickoff,
                                               venue, tie.id)
                self.tie_matches[tie.id].append(match_id)
        self.events.append(SeasonEvent(day, "paired", (stage.id,)))

    def _last_kickoffs(self, before: date, clubs: Sequence[str]) -> dict[str, datetime]:
        last: dict[str, datetime] = {}
        for m in self.matches.values():
            if m.kickoff.date() >= before:
                continue
            for c in (m.home_id, m.away_id):
                if c in clubs and (c not in last or m.kickoff > last[c]):
                    last[c] = m.kickoff
        return last

    def _finish_knockout(self, stage: KnockoutStageRule, day: date) -> None:
        self.stages_done.add(stage.id)
        self.events.append(SeasonEvent(day, "stage_complete", (stage.id,)))
        if stage.title is None:
            return
        tie = next(t for t in self.ties.values() if t.stage_id == stage.id)
        winner = self.tie_outcomes[tie.id].winner_id
        assert winner is not None
        self.titles[stage.track] = winner
        if stage.track == "main":
            self.runner_up = tie.low_id if winner == tie.high_id else tie.high_id
            self.events.append(SeasonEvent(day, "champion", (winner,)))
        else:
            self.events.append(SeasonEvent(day, "title", (stage.track, winner)))

    @property
    def complete(self) -> bool:
        return all(s.id in self.stages_done for s in self.ruleset.knockout_stages)

    def outcome(self) -> Outcome | None:
        if not self.complete:
            return None
        main_stages = [s for s in self.ruleset.knockout_stages if s.track == "main"]
        side: dict[str, list[str]] = {}
        for s in self.ruleset.knockout_stages:
            if s.track != "main" and s.track not in side:
                side[s.track] = self.stage_entrants[s.id]
        assert self.runner_up is not None
        return Outcome(
            champion=self.titles["main"], runner_up=self.runner_up,
            semifinalists=tuple(self.stage_entrants[main_stages[0].id]),
            side_entrants=side,
            side_titles={k: v for k, v in self.titles.items() if k != "main"},
            relegated=list(self.relegated), final_classification=self.overall,
        )

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
