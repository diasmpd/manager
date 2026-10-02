"""Builders for hand-made domain objects used across tests."""

from datetime import date

from manager_core.domain.attributes import ALL_ATTRIBUTES, Attributes
from manager_core.domain.player import Player
from manager_core.domain.positions import Position, PositionFamiliarity


def attrs(default: int = 10, **overrides: int) -> Attributes:
    values = dict.fromkeys(ALL_ATTRIBUTES, default)
    values.update(overrides)
    return Attributes(**values)


def player(
    pid: str = "p-1",
    positions: dict[Position, int] | None = None,
    attributes: Attributes | None = None,
    potential: int = 200,
    display_name: str | None = None,
    born: date = date(2000, 6, 15),
) -> Player:
    return Player(
        id=pid,
        full_name=f"Jogador {pid}",
        display_name=display_name or f"J {pid}",
        date_of_birth=born,
        nationalities=("BRA",),
        height_cm=180,
        weight_kg=75,
        left_foot=8,
        right_foot=20,
        attributes=attributes or attrs(),
        positions=PositionFamiliarity(positions or {Position.MC: 20}),
        potential_ability=potential,
    )
