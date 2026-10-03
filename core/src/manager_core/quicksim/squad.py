"""Team sheets: the starting XI (001's exact best XI) and the bench (research R7, R12)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from manager_core.domain.formation import Formation, load_catalogue
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.ratings.ability import current_ability, is_goalkeeper
from manager_core.ratings.lineup import best_assignment
from manager_core.ratings.suitability import suitability_milli

DEFAULT_FORMATION = "4-4-2"  # no tactics until spec 006
BENCH_SIZE = 9
NO_GOALKEEPER = "no_goalkeeper"
SHORT_SQUAD = "short_squad"


@dataclass(frozen=True, slots=True)
class TeamSheet:
    club_id: str
    formation: Formation
    starters: tuple[tuple[int, str], ...]  # (slot index, player id)
    bench: tuple[str, ...]
    flags: tuple[str, ...] = ()

    def slot_position(self, index: int) -> Position:
        return self.formation.slots[index].position

    @property
    def slot_positions(self) -> tuple[Position, ...]:
        return tuple(s.position for s in self.formation.slots)


def _by_ability(players: Sequence[Player]) -> list[Player]:
    return sorted(players, key=lambda p: (-current_ability(p), p.id))


def _bench(rest: Sequence[Player]) -> tuple[str, ...]:
    """The best players left, by CA, with a reserve goalkeeper first when there is one."""
    ranked = _by_ability(rest)
    keepers = [p for p in ranked if is_goalkeeper(p)]
    bench = keepers[:1] + [p for p in ranked if p not in keepers[:1]]
    return tuple(p.id for p in bench[:BENCH_SIZE])


def repair_team_sheet(base: TeamSheet, squad: Sequence[Player],
                      unavailable: frozenset[str]) -> TeamSheet:
    """The base sheet without unavailable players (spec 004 suspensions): each missing starter
    is replaced by the most suitable available player for his slot, the rest of the XI is
    kept, and the bench is refilled. Cheaper than a new exact XI, and what a manager does."""
    by_id = {p.id: p for p in squad}
    starters = dict(base.starters)
    taken = {pid for pid in starters.values() if pid not in unavailable}
    for slot in sorted(i for i, pid in starters.items() if pid in unavailable):
        position = base.slot_position(slot)
        candidates = [p for p in squad if p.id not in unavailable and p.id not in taken]
        if not candidates:
            del starters[slot]
            continue
        best = max(candidates, key=lambda p: (suitability_milli(p, position), p.id))
        starters[slot] = best.id
        taken.add(best.id)
    rest = [p for p in squad if p.id not in unavailable and p.id not in taken]
    flags = tuple(f for f in base.flags if f != SHORT_SQUAD)
    if len(starters) < len(base.formation.slots):
        flags = (*flags, SHORT_SQUAD)
    gk = next((pid for i, pid in starters.items() if base.slot_position(i) is Position.GK), None)
    if (gk is None or not is_goalkeeper(by_id[gk])) and NO_GOALKEEPER not in flags:
        flags = (*flags, NO_GOALKEEPER)
    return TeamSheet(base.club_id, base.formation, tuple(sorted(starters.items())), _bench(rest),
                     flags)


def build_team_sheet(club_id: str, squad: Sequence[Player],
                     formation_name: str = DEFAULT_FORMATION) -> TeamSheet:
    formation = load_catalogue()[formation_name]
    slots = [s.position for s in formation.slots]
    flags: list[str] = []
    if len(squad) >= len(slots):
        lineup = best_assignment(squad, slots)
        starters = tuple((a.slot_index, a.player_id) for a in lineup.assignments)
    else:  # fewer than 11 players: fill the most important slots, GK first
        flags.append(SHORT_SQUAD)
        order = sorted(range(len(slots)), key=lambda i: (slots[i] is not Position.GK, i))
        chosen = sorted(order[:len(squad)])
        lineup = best_assignment(squad, [slots[i] for i in chosen])
        starters = tuple((chosen[a.slot_index], a.player_id) for a in lineup.assignments)
    by_id = {p.id: p for p in squad}
    gk_slot = next((pid for i, pid in starters if slots[i] is Position.GK), None)
    if gk_slot is None or not is_goalkeeper(by_id[gk_slot]):
        flags.append(NO_GOALKEEPER)
    used = {pid for _, pid in starters}
    return TeamSheet(club_id, formation, starters, _bench([p for p in squad if p.id not in used]),
                     tuple(flags))
