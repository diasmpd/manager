"""Club entity (data-model.md "Club"). Constructor checks are invariants: import validation
runs first and reports problems with locations; these only catch programming errors."""

from __future__ import annotations

import re
from dataclasses import dataclass

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
ABBREVIATION = re.compile(r"^[A-Z]{3}$")
COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class ExternalRef:
    source: str
    source_id: str


@dataclass(frozen=True, slots=True)
class Club:
    id: str
    name: str
    short_name: str
    abbreviation: str
    city: str
    state: str | None
    country: str
    color_primary: str
    color_secondary: str
    stadium_name: str
    stadium_capacity: int
    founded_year: int
    reputation: int
    external_refs: tuple[ExternalRef, ...] = ()

    def __post_init__(self) -> None:
        if not SLUG.match(self.id):
            raise ValueError(f"invalid club id {self.id!r}")
        if not ABBREVIATION.match(self.abbreviation):
            raise ValueError(f"abbreviation must be exactly 3 uppercase letters: {self.abbreviation!r}")
        for colour in (self.color_primary, self.color_secondary):
            if not COLOUR.match(colour):
                raise ValueError(f"colour must be #RRGGBB: {colour!r}")
        if not 500 <= self.stadium_capacity <= 250_000:
            raise ValueError(f"stadium capacity out of range: {self.stadium_capacity}")
        if not 1 <= self.reputation <= 20:
            raise ValueError(f"reputation out of range: {self.reputation}")
