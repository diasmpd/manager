"""Football Manager's player attribute set (1-20), visible and hidden.

`ATTRIBUTE_GROUPS` is the single source of truth for names, grouping and FM display order.
CSV columns, validation and profile display are all derived from it.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum

MIN_VALUE = 1
MAX_VALUE = 20


class AttributeGroup(StrEnum):
    TECHNICAL = "technical"
    MENTAL = "mental"
    PHYSICAL = "physical"
    GOALKEEPING = "goalkeeping"
    HIDDEN = "hidden"


ATTRIBUTE_GROUPS: dict[AttributeGroup, tuple[str, ...]] = {
    AttributeGroup.TECHNICAL: (
        "corners", "crossing", "dribbling", "finishing", "first_touch", "free_kick_taking",
        "heading", "long_shots", "long_throws", "marking", "passing", "penalty_taking",
        "tackling", "technique",
    ),
    AttributeGroup.MENTAL: (
        "aggression", "anticipation", "bravery", "composure", "concentration", "decisions",
        "determination", "flair", "leadership", "off_the_ball", "positioning", "teamwork",
        "vision", "work_rate",
    ),
    AttributeGroup.PHYSICAL: (
        "acceleration", "agility", "balance", "jumping_reach", "natural_fitness", "pace",
        "stamina", "strength",
    ),
    AttributeGroup.GOALKEEPING: (
        "aerial_reach", "command_of_area", "communication", "eccentricity", "handling",
        "kicking", "one_on_ones", "punching", "reflexes", "rushing_out", "throwing",
    ),
    AttributeGroup.HIDDEN: (
        "adaptability", "ambition", "consistency", "controversy", "dirtiness",
        "important_matches", "injury_proneness", "loyalty", "pressure", "professionalism",
        "sportsmanship", "temperament", "versatility",
    ),
}

ALL_ATTRIBUTES: tuple[str, ...] = tuple(n for names in ATTRIBUTE_GROUPS.values() for n in names)
HIDDEN_ATTRIBUTES: tuple[str, ...] = ATTRIBUTE_GROUPS[AttributeGroup.HIDDEN]
VISIBLE_ATTRIBUTES: tuple[str, ...] = tuple(n for n in ALL_ATTRIBUTES if n not in HIDDEN_ATTRIBUTES)

# Neutral values used when a source has no hidden attributes (public data never does).
HIDDEN_DEFAULTS: dict[str, int] = {
    **dict.fromkeys(HIDDEN_ATTRIBUTES, 10),
    "dirtiness": 8,
    "injury_proneness": 8,
    "controversy": 6,
}

# FM shows goalkeepers a reduced technical panel.
GK_TECHNICAL: tuple[str, ...] = (
    "first_touch", "free_kick_taking", "passing", "penalty_taking", "technique",
)


@dataclass(frozen=True, slots=True)
class Attributes:
    # technical
    corners: int
    crossing: int
    dribbling: int
    finishing: int
    first_touch: int
    free_kick_taking: int
    heading: int
    long_shots: int
    long_throws: int
    marking: int
    passing: int
    penalty_taking: int
    tackling: int
    technique: int
    # mental
    aggression: int
    anticipation: int
    bravery: int
    composure: int
    concentration: int
    decisions: int
    determination: int
    flair: int
    leadership: int
    off_the_ball: int
    positioning: int
    teamwork: int
    vision: int
    work_rate: int
    # physical
    acceleration: int
    agility: int
    balance: int
    jumping_reach: int
    natural_fitness: int
    pace: int
    stamina: int
    strength: int
    # goalkeeping
    aerial_reach: int
    command_of_area: int
    communication: int
    eccentricity: int
    handling: int
    kicking: int
    one_on_ones: int
    punching: int
    reflexes: int
    rushing_out: int
    throwing: int
    # hidden
    adaptability: int
    ambition: int
    consistency: int
    controversy: int
    dirtiness: int
    important_matches: int
    injury_proneness: int
    loyalty: int
    pressure: int
    professionalism: int
    sportsmanship: int
    temperament: int
    versatility: int

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"attribute {f.name} must be an int, got {value!r}")
            if not MIN_VALUE <= value <= MAX_VALUE:
                raise ValueError(f"attribute {f.name}={value} outside {MIN_VALUE}-{MAX_VALUE}")

    def get(self, name: str) -> int:
        value: int = getattr(self, name)
        return value

    def as_dict(self) -> dict[str, int]:
        return {name: self.get(name) for name in ALL_ATTRIBUTES}


def visible_for(is_goalkeeper: bool) -> dict[AttributeGroup, tuple[str, ...]]:
    """Attribute groups shown on a player profile, in FM's order."""
    if is_goalkeeper:
        return {
            AttributeGroup.GOALKEEPING: ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING],
            AttributeGroup.MENTAL: ATTRIBUTE_GROUPS[AttributeGroup.MENTAL],
            AttributeGroup.PHYSICAL: ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL],
            AttributeGroup.TECHNICAL: GK_TECHNICAL,
        }
    return {
        group: ATTRIBUTE_GROUPS[group]
        for group in (AttributeGroup.TECHNICAL, AttributeGroup.MENTAL, AttributeGroup.PHYSICAL)
    }
