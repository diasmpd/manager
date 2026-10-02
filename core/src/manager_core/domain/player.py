"""Player entity (data-model.md "Player"). Age, CA and best position are derived, never stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from manager_core.domain.attributes import Attributes
from manager_core.domain.club import SLUG, ExternalRef
from manager_core.domain.positions import PositionFamiliarity


@dataclass(frozen=True, slots=True)
class Player:
    id: str
    full_name: str
    display_name: str
    date_of_birth: date
    nationalities: tuple[str, ...]
    height_cm: int
    weight_kg: int
    left_foot: int
    right_foot: int
    attributes: Attributes
    positions: PositionFamiliarity
    potential_ability: int
    external_refs: tuple[ExternalRef, ...] = ()

    def __post_init__(self) -> None:
        if not SLUG.match(self.id):
            raise ValueError(f"invalid player id {self.id!r}")
        if not 1 <= len(self.nationalities) <= 3:
            raise ValueError("a player has 1-3 nationalities")
        if not 150 <= self.height_cm <= 210:
            raise ValueError(f"height out of range: {self.height_cm}")
        if not 50 <= self.weight_kg <= 110:
            raise ValueError(f"weight out of range: {self.weight_kg}")
        for foot in (self.left_foot, self.right_foot):
            if not 1 <= foot <= 20:
                raise ValueError(f"foot ability out of range: {foot}")
        if max(self.left_foot, self.right_foot) < 15:
            raise ValueError("at least one foot must be >= 15")
        if not 1 <= self.potential_ability <= 200:
            raise ValueError(f"potential ability out of range: {self.potential_ability}")
        if not self.positions.natural_positions():
            raise ValueError("a player needs at least one position with familiarity >= 15")

    def age(self, reference_date: date) -> int:
        born = self.date_of_birth
        had_birthday = (reference_date.month, reference_date.day) >= (born.month, born.day)
        return reference_date.year - born.year - (0 if had_birthday else 1)
