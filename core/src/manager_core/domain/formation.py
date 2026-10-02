"""Formations as reference data (FR-014). Slots carry a position code for familiarity and
suitability, plus pitch coordinates in metres for later specs (006/007)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import resources

from manager_core.domain.positions import Position
from manager_core.io.dialect import read_text_table

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0


@dataclass(frozen=True, slots=True)
class FormationSlot:
    index: int
    position: Position
    x_m: float
    y_m: float

    def __post_init__(self) -> None:
        if not 0 <= self.x_m <= PITCH_LENGTH_M or not 0 <= self.y_m <= PITCH_WIDTH_M:
            raise ValueError(f"slot {self.index} outside the pitch")


@dataclass(frozen=True, slots=True)
class Formation:
    name: str
    slots: tuple[FormationSlot, ...]

    def __post_init__(self) -> None:
        if len(self.slots) != 11:
            raise ValueError(f"formation {self.name} must have exactly 11 slots")
        if sum(s.position is Position.GK for s in self.slots) != 1:
            raise ValueError(f"formation {self.name} must have exactly one GK")
        if [s.index for s in self.slots] != list(range(11)):
            raise ValueError(f"formation {self.name} slots must be indexed 0-10 in order")

    @property
    def positions(self) -> tuple[Position, ...]:
        return tuple(s.position for s in self.slots)


@cache
def load_catalogue() -> dict[str, Formation]:
    """Bundled formations, in file order."""
    text = resources.files("manager_core.reference").joinpath("formations.csv").read_text("utf-8-sig")
    grouped: dict[str, list[FormationSlot]] = {}
    for row in read_text_table(text).rows:
        v = row.values
        grouped.setdefault(v["formation"], []).append(
            FormationSlot(int(v["slot"]), Position(v["position"]), float(v["x_m"]), float(v["y_m"]))
        )
    return {name: Formation(name, tuple(slots)) for name, slots in grouped.items()}
