"""Dataset: the aggregate root holding clubs, players and memberships plus provenance.

Every collection is exposed in sorted-id order (Constitution II).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from types import MappingProxyType

from manager_core.domain.club import Club
from manager_core.domain.player import Player
from manager_core.domain.squad import SquadMembership


class RecordType(StrEnum):
    CLUB = "club"
    PLAYER = "player"


class FlagKind(StrEnum):
    HIDDEN_DEFAULTED = "hidden_defaulted"
    POTENTIAL_DEFAULTED = "potential_defaulted"
    POTENTIAL_RAISED = "potential_raised"


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    retrieved_on: date
    url: str | None = None
    licence_notes: str | None = None


@dataclass(frozen=True, slots=True)
class RecordFlag:
    record_type: RecordType
    record_id: str
    flag: FlagKind
    detail: str = ""

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.record_type.value, self.record_id, self.flag.value)


def _sorted_proxy[T](items: Mapping[str, T]) -> Mapping[str, T]:
    return MappingProxyType({k: items[k] for k in sorted(items)})


@dataclass(frozen=True, eq=True)
class Dataset:
    format_version: str
    reference_date: date
    fictional: bool
    tool: str
    tool_version: str
    sources: tuple[Source, ...]
    clubs: Mapping[str, Club]
    players: Mapping[str, Player]
    memberships: Mapping[str, SquadMembership]  # keyed by player_id (at most one per player)
    seed: int | None = None
    notes: str = ""
    record_flags: tuple[RecordFlag, ...] = field(default=())

    def __post_init__(self) -> None:
        object.__setattr__(self, "clubs", _sorted_proxy(self.clubs))
        object.__setattr__(self, "players", _sorted_proxy(self.players))
        object.__setattr__(self, "memberships", _sorted_proxy(self.memberships))
        unique = {f.key: f for f in self.record_flags}
        object.__setattr__(self, "record_flags", tuple(unique[k] for k in sorted(unique)))

    __hash__ = None  # type: ignore[assignment]  # holds mappings; compared by value only

    def club(self, club_id: str) -> Club:
        return self.clubs[club_id]

    def player(self, player_id: str) -> Player:
        return self.players[player_id]

    def membership(self, player_id: str) -> SquadMembership | None:
        return self.memberships.get(player_id)

    def squad(self, club_id: str) -> tuple[Player, ...]:
        return tuple(
            self.players[m.player_id] for m in self.memberships.values() if m.club_id == club_id
        )

    def free_agents(self) -> tuple[Player, ...]:
        return tuple(p for pid, p in self.players.items() if pid not in self.memberships)

    def flags_for(self, record_type: RecordType, record_id: str) -> tuple[RecordFlag, ...]:
        return tuple(
            f for f in self.record_flags if f.record_type is record_type and f.record_id == record_id
        )
