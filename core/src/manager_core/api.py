"""Core facade (contracts/facade.md): the only entry point UIs may call (Constitution III).

Returns plain immutable data, never formatted text. In 001 callers hold the Dataset object.
Spec 004 (saves) and 010 (out-of-process API) will replace it with a session/handle.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from manager_core.calibration import harness
from manager_core.calibration.harness import CalibrationReport
from manager_core.career import career as career_mod
from manager_core.career import rollover, store, views
from manager_core.career import selection as selection_mod
from manager_core.career.career import Career, SeasonRecord, Stop
from manager_core.career.discipline import Discipline
from manager_core.career.selection import Selection, SelectionIssue
from manager_core.career.store import SaveSummary
from manager_core.career.views import FeedLine, NewsItem, SquadRow
from manager_core.competition import rules
from manager_core.competition.calendar import CalendarDay
from manager_core.competition.results import Result, ResultProvider
from manager_core.competition.rules import Ruleset, RulesetReport, RulesetSummary
from manager_core.competition.season import Match, Outcome, Season, SeasonEvent
from manager_core.competition.standings import TableRow
from manager_core.domain.attributes import (
    ATTRIBUTE_GROUPS,
    AttributeGroup,
    visible_for,
)
from manager_core.domain.dataset import Dataset
from manager_core.domain.formation import Formation, load_catalogue
from manager_core.domain.player import Player
from manager_core.domain.positions import FamiliarityBand, Position, band_for
from manager_core.io import reader, writer
from manager_core.io.reader import LoadResult
from manager_core.io.validate import ValidationReport
from manager_core.io.writer import ExportSummary
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import MatchReport
from manager_core.ratings import lineup
from manager_core.ratings.ability import best_position, current_ability, is_goalkeeper
from manager_core.ratings.lineup import Lineup
from manager_core.ratings.suitability import suitability_milli

SquadSort = Literal["position", "ca", "age", "number"]
DEFAULT_SEED = 20261002
DEFAULT_RULESET = "mg-modulo-i-2026"  # the CLI default (contracts/cli.md)

__all__ = [
    "ClubSummary",
    "ExportSummary",
    "Lineup",
    "LoadResult",
    "NotFoundError",
    "PlayerProfile",
    "PositionRanking",
    "SquadEntry",
    "ValidationReport",
    "export_dataset",
    "generate_sample",
    "list_clubs",
    "list_formations",
    "load_dataset",
    "player_profile",
    "rank_for_position",
    "squad",
    "suggest_lineup",
    "validate_dataset",
]


class NotFoundError(LookupError):
    def __init__(self, kind: str, id: str) -> None:
        super().__init__(f"{kind} not found: {id}")
        self.kind = kind
        self.id = id


# ---- result types --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClubSummary:
    id: str
    name: str
    abbreviation: str
    city: str
    state: str | None
    reputation: int
    squad_size: int
    average_ca: int


@dataclass(frozen=True, slots=True)
class SquadEntry:
    player_id: str
    shirt_number: int | None
    display_name: str
    label: str  # display name, disambiguated within the squad when needed
    age: int
    best_position: Position
    band: FamiliarityBand
    suitability_milli: int
    current_ability: int


@dataclass(frozen=True, slots=True)
class PositionFamiliarityEntry:
    position: Position
    value: int
    band: FamiliarityBand


@dataclass(frozen=True, slots=True)
class AttributeGroupView:
    group: AttributeGroup
    values: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    player_id: str
    full_name: str
    display_name: str
    date_of_birth: date
    age: int
    nationalities: tuple[str, ...]
    height_cm: int
    weight_kg: int
    left_foot: int
    right_foot: int
    club_id: str | None
    club_name: str | None
    shirt_number: int | None
    is_goalkeeper: bool
    best_position: Position
    positions: tuple[PositionFamiliarityEntry, ...]  # familiarity > 1, FM order
    attributes: tuple[AttributeGroupView, ...]  # visible groups, FM display order
    current_ability: int
    potential_ability: int | None  # only with include_hidden
    hidden: AttributeGroupView | None  # only with include_hidden


@dataclass(frozen=True, slots=True)
class PositionRanking:
    player_id: str
    label: str
    band: FamiliarityBand
    suitability_milli: int


# ---- data in / out -------------------------------------------------------------------------


def load_dataset(path: Path) -> LoadResult:
    return reader.load(path)


def validate_dataset(path: Path) -> ValidationReport:
    return reader.load(path).report


def export_dataset(dataset: Dataset, path: Path) -> ExportSummary:
    return writer.write(dataset, path)


def generate_sample(seed: int = DEFAULT_SEED) -> Dataset:
    from manager_core.sample.generator import generate

    return generate(seed)


# ---- browsing ------------------------------------------------------------------------------


def _club_players(dataset: Dataset, club_id: str) -> tuple[Player, ...]:
    if club_id not in dataset.clubs:
        raise NotFoundError("club", club_id)
    return dataset.squad(club_id)


def _labels(dataset: Dataset, players: tuple[Player, ...]) -> dict[str, str]:
    """Display names, disambiguated when two players in the list share one (e.g. two Gabriels)."""
    counts: dict[str, int] = {}
    for p in players:
        counts[p.display_name] = counts.get(p.display_name, 0) + 1
    labels: dict[str, str] = {}
    for p in players:
        if counts[p.display_name] == 1:
            labels[p.id] = p.display_name
            continue
        membership = dataset.membership(p.id)
        if membership and membership.shirt_number is not None:
            labels[p.id] = f"{p.display_name} ({membership.shirt_number})"
        else:
            labels[p.id] = f"{p.display_name} ({p.date_of_birth.year})"
    return labels


def list_clubs(dataset: Dataset) -> list[ClubSummary]:
    result = []
    for club in dataset.clubs.values():
        players = dataset.squad(club.id)
        avg = round(sum(current_ability(p) for p in players) / len(players)) if players else 0
        result.append(
            ClubSummary(
                id=club.id,
                name=club.name,
                abbreviation=club.abbreviation,
                city=club.city,
                state=club.state,
                reputation=club.reputation,
                squad_size=len(players),
                average_ca=avg,
            )
        )
    return sorted(result, key=lambda c: (-c.reputation, c.name, c.id))


_SQUAD_SORTS: dict[str, Callable[[SquadEntry], tuple[object, ...]]] = {
    "position": lambda e: (e.best_position.order, -e.current_ability, e.player_id),
    "ca": lambda e: (-e.current_ability, e.player_id),
    "age": lambda e: (e.age, e.player_id),
    "number": lambda e: (e.shirt_number is None, e.shirt_number or 0, e.player_id),
}


def squad(dataset: Dataset, club_id: str, sort: SquadSort = "position") -> list[SquadEntry]:
    players = _club_players(dataset, club_id)
    labels = _labels(dataset, players)
    entries = []
    for p in players:
        best = best_position(p)
        membership = dataset.membership(p.id)
        entries.append(
            SquadEntry(
                player_id=p.id,
                shirt_number=membership.shirt_number if membership else None,
                display_name=p.display_name,
                label=labels[p.id],
                age=p.age(dataset.reference_date),
                best_position=best,
                band=band_for(p.positions[best]),
                suitability_milli=suitability_milli(p, best),
                current_ability=current_ability(p),
            )
        )
    return sorted(entries, key=_SQUAD_SORTS[sort])


def player_profile(
    dataset: Dataset, player_id: str, include_hidden: bool = False
) -> PlayerProfile:
    if player_id not in dataset.players:
        raise NotFoundError("player", player_id)
    p = dataset.player(player_id)
    membership = dataset.membership(player_id)
    club = dataset.clubs.get(membership.club_id) if membership else None
    gk = is_goalkeeper(p)
    groups = tuple(
        AttributeGroupView(group, tuple((n, p.attributes.get(n)) for n in names))
        for group, names in visible_for(gk).items()
    )
    hidden_names = ATTRIBUTE_GROUPS[AttributeGroup.HIDDEN]
    return PlayerProfile(
        player_id=p.id,
        full_name=p.full_name,
        display_name=p.display_name,
        date_of_birth=p.date_of_birth,
        age=p.age(dataset.reference_date),
        nationalities=p.nationalities,
        height_cm=p.height_cm,
        weight_kg=p.weight_kg,
        left_foot=p.left_foot,
        right_foot=p.right_foot,
        club_id=club.id if club else None,
        club_name=club.name if club else None,
        shirt_number=membership.shirt_number if membership else None,
        is_goalkeeper=gk,
        best_position=best_position(p),
        positions=tuple(
            PositionFamiliarityEntry(pos, p.positions[pos], band_for(p.positions[pos]))
            for pos in Position
            if p.positions[pos] > 1
        ),
        attributes=groups,
        current_ability=current_ability(p),
        potential_ability=p.potential_ability if include_hidden else None,
        hidden=(
            AttributeGroupView(
                AttributeGroup.HIDDEN, tuple((n, p.attributes.get(n)) for n in hidden_names)
            )
            if include_hidden
            else None
        ),
    )


# ---- who plays where -----------------------------------------------------------------------


def rank_for_position(dataset: Dataset, club_id: str, position: Position) -> list[PositionRanking]:
    players = _club_players(dataset, club_id)
    labels = _labels(dataset, players)
    return [
        PositionRanking(p.id, labels[p.id], band_for(p.positions[position]), score)
        for p, score in lineup.rank_for_position(players, position)
    ]


def suggest_lineup(dataset: Dataset, club_id: str, formation: str = "4-4-2") -> Lineup:
    catalogue = load_catalogue()
    if formation not in catalogue:
        raise NotFoundError("formation", formation)
    return lineup.best_xi(_club_players(dataset, club_id), catalogue[formation])


def list_formations() -> list[Formation]:
    return list(load_catalogue().values())


# ---- competitions (spec 002) -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupView:
    label: str
    club_ids: tuple[str, ...]
    club_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchView:
    id: str
    stage_id: str
    round: int
    kickoff: datetime
    home_id: str
    home_name: str
    away_id: str
    away_name: str
    venue: str
    result: Result | None


def list_rulesets() -> list[RulesetSummary]:
    return rules.list_rulesets()


def load_ruleset(ruleset_id: str) -> Ruleset:
    try:
        return rules.load_ruleset(ruleset_id)
    except rules.RulesetNotFoundError:
        raise NotFoundError("ruleset", ruleset_id) from None


def validate_ruleset(path: Path) -> RulesetReport:
    return rules.validate_ruleset_file(path)


def start_season(dataset: Dataset, ruleset_id: str, year: int, master_seed: int,
                 participants: Sequence[str] | None = None, *,
                 result_provider: ResultProvider | None = None) -> Season:
    """Participants default to the clubs of the ruleset's state, sorted by id."""
    for club_id in participants or ():
        if club_id not in dataset.clubs:
            raise NotFoundError("club", club_id)
    provider = result_provider or QuickSimProvider(dataset)
    return Season.start(dataset, load_ruleset(ruleset_id), year, master_seed, participants,
                        provider)


def season_groups(season: Season) -> list[GroupView]:
    return [GroupView(g.label, g.club_ids, tuple(season.club_name(c) for c in g.club_ids))
            for g in season.groups]


def _match_view(season: Season, m: Match) -> MatchView:
    return MatchView(m.id, m.stage_id, m.round, m.kickoff, m.home_id, season.club_name(m.home_id),
                     m.away_id, season.club_name(m.away_id), m.venue, season.results.get(m.id))


def match_view(season: Season, match_id: str) -> MatchView:
    if match_id not in season.matches:
        raise NotFoundError("match", match_id)
    return _match_view(season, season.matches[match_id])


def season_fixtures(season: Season, club_id: str | None = None,
                    round: int | None = None) -> list[MatchView]:
    if club_id is not None and club_id not in season.participants:
        raise NotFoundError("club", club_id)
    return [
        _match_view(season, m) for m in season.sorted_matches()
        if (club_id is None or club_id in (m.home_id, m.away_id))
        and (round is None or (m.stage_id == season.ruleset.group_stage.id and m.round == round))
    ]


@dataclass(frozen=True, slots=True)
class TieView:
    id: str
    stage_id: str
    track: str
    high_id: str
    high_name: str
    low_id: str
    low_name: str
    legs: tuple[MatchView, ...]
    winner_id: str | None
    decided_by: str | None


@dataclass(frozen=True, slots=True)
class DayView:
    day: date
    matches: tuple[MatchView, ...]
    events: tuple[SeasonEvent, ...]


def advance_to(season: Season, day: date) -> list[SeasonEvent]:
    return season.advance_to(day)


def season_table(season: Season, group: str | None = None) -> list[TableRow]:
    """A group table, or the overall classification (group=None), with zones once decided."""
    if group is not None and group not in {g.label for g in season.groups}:
        raise NotFoundError("group", group)
    rows = season.group_table(group) if group is not None else season.overall_table()
    zones: dict[str, str] = {}
    for track in season.ruleset.tracks():
        first = season.ruleset.first_stage_of(track)
        for club in season.stage_entrants.get(first.id, []):
            zones.setdefault(club, f"track:{track}")
    for club in season.relegated:
        zones[club] = "relegated"
    return [dataclasses.replace(r, zone=zones.get(r.club_id)) for r in rows]


def season_bracket(season: Season) -> list[TieView]:
    views = []
    for tie in sorted(season.ties.values(), key=lambda t: (
            [s.id for s in season.ruleset.stages].index(t.stage_id), t.id)):
        outcome = season.tie_outcomes.get(tie.id)
        legs = tuple(_match_view(season, season.matches[m]) for m in season.tie_matches[tie.id])
        views.append(TieView(tie.id, tie.stage_id, tie.track, tie.high_id,
                             season.club_name(tie.high_id), tie.low_id,
                             season.club_name(tie.low_id), legs,
                             outcome.winner_id if outcome else None,
                             outcome.decided_by if outcome else None))
    return views


def season_day(season: Season, day: date) -> DayView:
    matches = tuple(_match_view(season, m) for m in season.sorted_matches()
                    if m.kickoff.date() == day)
    return DayView(day, matches, tuple(e for e in season.events if e.day == day))


def season_outcomes(season: Season) -> Outcome | None:
    return season.outcome()


def season_calendar(season: Season, month: int | None = None) -> list[CalendarDay]:
    """Every day of the season's year, or of one month (1-12)."""
    calendar = season.calendar()
    if month is None:
        return list(calendar.days)
    if not 1 <= month <= 12:
        raise NotFoundError("month", str(month))
    return list(calendar.month(month))


# ---- quick sim (spec 003) --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MatchReportView:
    match: MatchView
    report: MatchReport | None  # None until played (or for placeholder results)


@dataclass(frozen=True, slots=True)
class ScorerRow:
    player_id: str
    player_name: str
    club_id: str
    club_name: str
    goals: int
    penalties: int
    assists: int


def match_report(season: Season, match_id: str) -> MatchReportView:
    view = match_view(season, match_id)
    return MatchReportView(view, view.result.report if view.result else None)


def season_scorers(season: Season, limit: int | None = None) -> list[ScorerRow]:
    """Top scorers: goals, then assists, then fewer penalties, then player id."""
    goals: dict[str, int] = {}
    penalties: dict[str, int] = {}
    assists: dict[str, int] = {}
    club_of: dict[str, str] = {}
    for match_id in sorted(season.results):
        report = season.results[match_id].report
        if report is None:
            continue
        match = season.matches[match_id]
        clubs = {"home": match.home_id, "away": match.away_id}
        for e in report.events:
            if e.kind in ("goal", "penalty_goal"):
                goals[e.player_id] = goals.get(e.player_id, 0) + 1
                club_of[e.player_id] = clubs[e.side]
                if e.kind == "penalty_goal":
                    penalties[e.player_id] = penalties.get(e.player_id, 0) + 1
                if e.other_player_id:
                    assists[e.other_player_id] = assists.get(e.other_player_id, 0) + 1
                    club_of.setdefault(e.other_player_id, clubs[e.side])
    ids = sorted(set(goals) | set(assists), key=lambda pid: (
        -goals.get(pid, 0), -assists.get(pid, 0), penalties.get(pid, 0), pid))
    rows = [ScorerRow(pid, season.dataset.player(pid).display_name, club_of[pid],
                      season.club_name(club_of[pid]), goals.get(pid, 0),
                      penalties.get(pid, 0), assists.get(pid, 0))
            for pid in ids if goals.get(pid, 0) > 0]
    return rows[:limit] if limit is not None else rows


def run_calibration(dataset: Dataset, gate: str = "pr",
                    baseline: Path | None = None) -> CalibrationReport:
    """Run a calibration gate (deterministic; writes nothing)."""
    return harness.run(dataset, gate, baseline=baseline)


# ---- careers (spec 004) ----------------------------------------------------------------------


def new_career(dataset: Dataset, name: str, club_id: str, master_seed: int | None = None,
               ruleset_id: str = DEFAULT_RULESET, year: int = 2027) -> Career:
    store.check_name(name)
    try:
        return career_mod.new_career(dataset, name, club_id, master_seed, ruleset_id, year)
    except career_mod.UnknownClubError:
        raise NotFoundError("club", club_id) from None


def load_career(saves: Path, name: str) -> Career:
    try:
        career = store.load(saves, name)
    except store.SaveNotFoundError:
        raise NotFoundError("save", name) from None
    apply_selection(career)
    return career


def save_career(career: Career, saves: Path, name: str | None = None) -> Path:
    return store.save(career, saves, name)


def list_saves(saves: Path) -> list[SaveSummary]:
    return store.list_saves(saves)


def delete_save(saves: Path, name: str) -> None:
    try:
        store.delete(saves, name)
    except store.SaveNotFoundError:
        raise NotFoundError("save", name) from None


def continue_career(career: Career, saves: Path, *, to_season_end: bool = False) -> Stop:
    """Play to the next stop, autosaving weekly; the career is saved under its name."""

    def autosave(c: Career) -> None:
        store.save(c, saves, store.AUTOSAVE, allow_autosave=True)

    def next_season(c: Career) -> None:
        rollover.next_season(c)
        apply_selection(c)  # the new season has a new provider; keep the user's choice

    stop = career_mod.continue_(career, autosave, next_season)
    while to_season_end and stop.kind != career_mod.SEASON_END:
        stop = career_mod.continue_(career, autosave, next_season)
    store.save(career, saves)
    return stop


@dataclass(frozen=True, slots=True)
class SuspensionView:
    player_id: str
    player_name: str
    matches: int


@dataclass(frozen=True, slots=True)
class CareerStatus:
    name: str
    club_id: str
    club_name: str
    current_date: date
    year: int
    next_match: MatchView | None
    position: int | None  # place in the overall table (None before the first match)
    suspended: tuple[SuspensionView, ...]
    pending: Stop | None


def suspended_players(career: Career, club_id: str) -> list[SuspensionView]:
    ledger = career.season.discipline
    if not isinstance(ledger, Discipline):
        return []
    return [SuspensionView(pid, career.world.player(pid).display_name, ledger.bans(pid))
            for pid in sorted(ledger.suspended(club_id))]


def career_status(career: Career) -> CareerStatus:
    season = career.season
    club = career.user_club_id
    upcoming = [m for m in season.sorted_matches()
                if m.id not in season.results and club in (m.home_id, m.away_id)]
    rows = season_table(season) if season.results else []
    place = next((r.place for r in rows if r.club_id == club), None)
    return CareerStatus(career.name, club, season.club_name(club), career.current_date,
                        season.year, _match_view(season, upcoming[0]) if upcoming else None,
                        place, tuple(suspended_players(career, club)), career.pending)


def career_history(career: Career) -> list[SeasonRecord]:
    return list(career.history)


# ---- team selection (spec 005) ---------------------------------------------------------------


class SelectionError(ValueError):
    def __init__(self, issues: list[SelectionIssue]) -> None:
        super().__init__(", ".join(f"{i.code}:{i.player_id}" for i in issues))
        self.issues = issues


def propose_selection(career: Career, formation: str | None = None) -> Selection:
    """The assistant's XI and bench, for the given formation or the current selection's."""
    if formation is None:
        formation = career.selection.formation if career.selection else "4-4-2"
    return selection_mod.propose(career, formation)


def validate_selection(career: Career, selection: Selection) -> list[SelectionIssue]:
    return selection_mod.validate(career, selection)


def apply_selection(career: Career) -> None:
    """Re-apply the career's selection to its season (after load or rollover); a selection that
    is no longer valid (players left or are suspended) is dropped."""
    sel = career.selection
    if sel is not None and any(i.severity == "error"
                               for i in selection_mod.validate(career, sel)):
        career.selection = sel = None
    career.live_provider.override(
        career.user_club_id,
        None if sel is None else selection_mod.to_team_sheet(career, sel))


def confirm_selection(career: Career, selection: Selection) -> list[SelectionIssue]:
    """Confirm the user's selection; errors refuse it, warnings are returned."""
    issues = selection_mod.validate(career, selection)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise SelectionError(errors)
    career.selection = selection
    apply_selection(career)
    return issues


# ---- views for clients (spec 005) ------------------------------------------------------------


def match_feed(season: Season, match_id: str) -> list[FeedLine]:
    if match_id not in season.matches:
        raise NotFoundError("match", match_id)
    return views.match_feed(season, match_id)


def career_news(career: Career) -> list[NewsItem]:
    return views.career_news(career)


def squad_view(career: Career) -> list[SquadRow]:
    return views.squad_view(career)


def last_user_match(career: Career) -> str | None:
    """The user club's most recently played match, or None."""
    season = career.season
    played = [m for m in season.sorted_matches() if m.id in season.results
              and career.user_club_id in (m.home_id, m.away_id)]
    return played[-1].id if played else None
