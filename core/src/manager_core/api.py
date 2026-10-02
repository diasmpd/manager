"""Core facade (contracts/facade.md): the only entry point UIs may call (Constitution III).

Returns plain immutable data, never formatted text. In 001 callers hold the Dataset object.
Spec 004 (saves) and 010 (out-of-process API) will replace it with a session/handle.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from manager_core.competition import rules
from manager_core.competition.results import Result, ResultProvider
from manager_core.competition.rules import Ruleset, RulesetReport, RulesetSummary
from manager_core.competition.season import Match, Season
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
from manager_core.ratings import lineup
from manager_core.ratings.ability import best_position, current_ability, is_goalkeeper
from manager_core.ratings.lineup import Lineup
from manager_core.ratings.suitability import suitability_milli

SquadSort = Literal["position", "ca", "age", "number"]
DEFAULT_SEED = 20261002

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
    return Season.start(dataset, load_ruleset(ruleset_id), year, master_seed, participants,
                        result_provider)


def season_groups(season: Season) -> list[GroupView]:
    return [GroupView(g.label, g.club_ids, tuple(season.club_name(c) for c in g.club_ids))
            for g in season.groups]


def _match_view(season: Season, m: Match) -> MatchView:
    return MatchView(m.id, m.stage_id, m.round, m.kickoff, m.home_id, season.club_name(m.home_id),
                     m.away_id, season.club_name(m.away_id), m.venue, season.results.get(m.id))


def season_fixtures(season: Season, club_id: str | None = None,
                    round: int | None = None) -> list[MatchView]:
    if club_id is not None and club_id not in season.participants:
        raise NotFoundError("club", club_id)
    return [
        _match_view(season, m) for m in season.sorted_matches()
        if (club_id is None or club_id in (m.home_id, m.away_id))
        and (round is None or (m.stage_id == season.ruleset.group_stage.id and m.round == round))
    ]
