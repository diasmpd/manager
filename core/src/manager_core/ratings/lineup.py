"""Who plays where (FR-013, research R9).

Exact best assignment by bitmask dynamic programming over the slots, on integer milli-point
scores so ties are exact and machine-independent. Tie-break: higher total, then the
lexicographically smaller tuple of player ids in slot order.

Principle of optimality for the tie-break: two partial assignments with the same filled-slot
mask get identical completions, so their final id tuples differ only on the filled slots.
Keeping the lexicographically smaller partial tuple per mask is therefore exact.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from manager_core.domain.formation import Formation
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.ratings.ability import is_goalkeeper
from manager_core.ratings.suitability import suitability_milli

_EMPTY = ""  # sorts before any player id, only ever compared against itself (same mask)


@dataclass(frozen=True, slots=True)
class LineupAssignment:
    slot_index: int
    position: Position
    player_id: str
    suitability_milli: int


@dataclass(frozen=True, slots=True)
class Lineup:
    formation: str
    assignments: tuple[LineupAssignment, ...]
    total_milli: int
    flags: tuple[str, ...]


def rank_for_position(players: Iterable[Player], position: Position) -> list[tuple[Player, int]]:
    scored = [(p, suitability_milli(p, position)) for p in players]
    return sorted(scored, key=lambda item: (-item[1], item[0].id))


def best_assignment(players: Iterable[Player], slots: Sequence[Position]) -> Lineup:
    """Optimal assignment of distinct players to the given slots."""
    ordered = sorted(players, key=lambda p: p.id)
    n_slots = len(slots)
    if len(ordered) < n_slots:
        raise ValueError(f"need at least {n_slots} players, got {len(ordered)}")
    scores = [[suitability_milli(p, s) for s in slots] for p in ordered]

    # dp[mask] = (total, ids in slot order with _EMPTY for unfilled slots)
    dp: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, (_EMPTY,) * n_slots)}
    for p_index, player in enumerate(ordered):
        row = scores[p_index]
        updates: dict[int, tuple[int, tuple[str, ...]]] = {}
        for mask, (total, ids) in dp.items():
            for slot in range(n_slots):
                bit = 1 << slot
                if mask & bit:
                    continue
                new_mask = mask | bit
                candidate = (total + row[slot], ids[:slot] + (player.id,) + ids[slot + 1 :])
                current = updates.get(new_mask) or dp.get(new_mask)
                if current is None or _better(candidate, current):
                    updates[new_mask] = candidate
        for mask, value in updates.items():
            existing = dp.get(mask)
            if existing is None or _better(value, existing):
                dp[mask] = value

    total, ids = dp[(1 << n_slots) - 1]
    by_id = {p.id: i for i, p in enumerate(ordered)}
    assignments = tuple(
        LineupAssignment(i, slots[i], pid, scores[by_id[pid]][i]) for i, pid in enumerate(ids)
    )
    flags = tuple(
        "outfield_in_goal"
        for a in assignments
        if a.position is Position.GK and not is_goalkeeper(ordered[by_id[a.player_id]])
    )
    return Lineup("", assignments, total, flags)


def _better(a: tuple[int, tuple[str, ...]], b: tuple[int, tuple[str, ...]]) -> bool:
    return a[0] > b[0] or (a[0] == b[0] and a[1] < b[1])


def best_xi(players: Iterable[Player], formation: Formation) -> Lineup:
    result = best_assignment(players, formation.positions)
    return Lineup(formation.name, result.assignments, result.total_milli, result.flags)
