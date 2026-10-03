"""Team ratings from the FM attributes of the players on the pitch (research R2).

Each composite is a weighted sum over the players on the pitch, divided by the weight of a full
XI in the same formation. A missing player (sent off) therefore lowers every composite he
contributed to. Contributions are scaled by the player's familiarity with his slot.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from manager_core.domain.player import Player
from manager_core.domain.positions import NATURAL_THRESHOLD, Position, familiarity_factor


class Group(StrEnum):
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    ATTACKING_MID = "attacking_mid"
    FORWARD = "forward"


POSITION_GROUP: dict[Position, Group] = {
    Position.GK: Group.GOALKEEPER,
    **dict.fromkeys((Position.DL, Position.DC, Position.DR, Position.WBL, Position.WBR),
                    Group.DEFENDER),
    **dict.fromkeys((Position.DM, Position.ML, Position.MC, Position.MR), Group.MIDFIELDER),
    **dict.fromkeys((Position.AML, Position.AMC, Position.AMR), Group.ATTACKING_MID),
    Position.ST: Group.FORWARD,
}

# composite -> (attributes, weight per group: GK, DEF, MID, AM, ATT)
_ATTACK = ("finishing", "off_the_ball", "composure", "dribbling", "first_touch", "technique",
           "anticipation", "pace", "acceleration")
_CONTROL = ("passing", "vision", "decisions", "technique", "first_touch", "teamwork",
            "work_rate", "stamina")
_DEFENCE = ("marking", "tackling", "positioning", "anticipation", "concentration", "heading",
            "strength", "jumping_reach", "pace")
_GOALKEEPING = ("reflexes", "handling", "one_on_ones", "aerial_reach", "command_of_area",
                "agility", "concentration", "positioning")
_SET_PIECES = ("corners", "free_kick_taking", "heading", "jumping_reach")

_WEIGHTS: dict[str, tuple[float, float, float, float, float]] = {
    "attack": (0.0, 0.15, 0.5, 0.75, 1.0),
    "control": (0.0, 0.4, 1.0, 0.7, 0.4),
    "defence": (0.0, 1.0, 0.5, 0.25, 0.1),
    "goalkeeping": (1.0, 0.0, 0.0, 0.0, 0.0),
    "set_pieces": (0.0, 0.5, 0.5, 0.5, 0.5),
    "discipline": (0.0, 1.0, 0.8, 0.5, 0.4),
}
_GROUP_INDEX = {g: i for i, g in enumerate(Group)}
STAND_IN_KEEPER = 0.5


@dataclass(frozen=True, slots=True)
class TeamRatings:
    """Composites on the 1-20 attribute scale (discipline: higher = more fouls and cards)."""

    attack: float
    control: float
    defence: float
    goalkeeping: float
    set_pieces: float
    discipline: float


def _mean(player: Player, names: Sequence[str]) -> float:
    return sum(player.attributes.get(n) for n in names) / len(names)


def discipline_score(player: Player) -> float:
    """Foul and card proneness on the 1-20 scale (research R5). Aggression is the main driver,
    as in FM; poor tackling adds clumsy fouls."""
    a = player.attributes
    return (0.45 * a.get("aggression") + 0.25 * a.get("dirtiness")
            + 0.2 * (21 - a.get("temperament")) + 0.1 * (21 - a.get("tackling")))


def player_composites(player: Player) -> dict[str, float]:
    return {
        "attack": _mean(player, _ATTACK),
        "control": _mean(player, _CONTROL),
        "defence": _mean(player, _DEFENCE),
        "goalkeeping": _mean(player, _GOALKEEPING),
        "set_pieces": _mean(player, _SET_PIECES),
        "discipline": discipline_score(player),
    }


Composites = Mapping[str, float]


def contribution(player: Player, slot: Position, composite: str,
                 composites: Composites | None = None) -> float:
    """What one player adds to a composite from a slot (before dividing by the full XI).
    `composites` are the player's precomputed `player_composites` (a speed-up)."""
    weight = _WEIGHTS[composite][_GROUP_INDEX[POSITION_GROUP[slot]]]
    if weight == 0:
        return 0.0
    value = (composites or player_composites(player))[composite]
    if composite != "discipline":  # an unfamiliar slot hurts quality, not temperament
        value *= familiarity_factor(player.positions[slot])
    if slot is Position.GK and player.positions[slot] < NATURAL_THRESHOLD:
        value *= STAND_IN_KEEPER  # an outfield player in goal (spec edge case)
    return weight * value


def full_weight(slots: Sequence[Position], composite: str) -> float:
    return sum(_WEIGHTS[composite][_GROUP_INDEX[POSITION_GROUP[s]]] for s in slots)


def slot_contributions(player: Player, slot: Position,
                       composites: Composites | None = None) -> tuple[float, ...]:
    """The player's contribution to every composite from a slot, in `COMPOSITES` order."""
    comps = composites or player_composites(player)
    return tuple(contribution(player, slot, c, comps) for c in COMPOSITES)


COMPOSITES = tuple(_WEIGHTS)


def combine(contributions: Sequence[tuple[Position, tuple[float, ...]]],
            formation_slots: Sequence[Position], defence_penalty: float = 0.0) -> TeamRatings:
    """Ratings from per-player slot contributions (see `rate`)."""
    values = {}
    for k, composite in enumerate(COMPOSITES):
        total = sum(c[k] for _, c in contributions)
        if composite == "defence":
            total -= defence_penalty
        if composite == "discipline":
            # a mean: fewer players do not mean fewer fouls per player
            denominator = sum(_WEIGHTS[composite][_GROUP_INDEX[POSITION_GROUP[s]]]
                              for s, _ in contributions) or 1.0
            values[composite] = total / denominator
        else:
            full = full_weight(formation_slots, composite)
            values[composite] = max(1.0, total / full) if full else 1.0
    return TeamRatings(**values)


def rate(on_pitch: Sequence[tuple[Position, Player]], formation_slots: Sequence[Position],
         defence_penalty: float = 0.0,
         composites: Mapping[str, Composites] | None = None) -> TeamRatings:
    """Ratings of the players on the pitch. `defence_penalty` is subtracted from the defence
    sum (the caution behaviour's cost, research R5)."""
    ordered = sorted(on_pitch, key=lambda sp: sp[1].id)
    return combine([(slot, slot_contributions(p, slot, composites.get(p.id) if composites
                                              else None)) for slot, p in ordered],
                   formation_slots, defence_penalty)
