"""FM position codes, lines, familiarity bands and the familiarity penalty."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from enum import StrEnum

MIN_FAMILIARITY = 1
MAX_FAMILIARITY = 20
NATURAL_THRESHOLD = 15  # familiarity >= 15 counts as a "real" position (Natural/Accomplished)


class Line(StrEnum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    ATT = "ATT"


class Position(StrEnum):
    # FM order
    GK = "GK"
    DL = "DL"
    DC = "DC"
    DR = "DR"
    WBL = "WBL"
    WBR = "WBR"
    DM = "DM"
    ML = "ML"
    MC = "MC"
    MR = "MR"
    AML = "AML"
    AMC = "AMC"
    AMR = "AMR"
    ST = "ST"

    @property
    def line(self) -> Line:
        return _LINES[self]

    @property
    def order(self) -> int:
        return _ORDER[self]


_LINES: dict[Position, Line] = {
    Position.GK: Line.GK,
    **dict.fromkeys(
        (Position.DL, Position.DC, Position.DR, Position.WBL, Position.WBR), Line.DEF
    ),
    **dict.fromkeys((Position.DM, Position.ML, Position.MC, Position.MR), Line.MID),
    **dict.fromkeys((Position.AML, Position.AMC, Position.AMR, Position.ST), Line.ATT),
}
_ORDER: dict[Position, int] = {p: i for i, p in enumerate(Position)}


class FamiliarityBand(StrEnum):
    NATURAL = "natural"
    ACCOMPLISHED = "accomplished"
    COMPETENT = "competent"
    UNCONVINCING = "unconvincing"
    AWKWARD = "awkward"
    INEFFECTUAL = "ineffectual"


_BAND_FLOORS: tuple[tuple[int, FamiliarityBand], ...] = (
    (18, FamiliarityBand.NATURAL),
    (15, FamiliarityBand.ACCOMPLISHED),
    (12, FamiliarityBand.COMPETENT),
    (9, FamiliarityBand.UNCONVINCING),
    (5, FamiliarityBand.AWKWARD),
    (1, FamiliarityBand.INEFFECTUAL),
)

# Research R7: penalty anchors after FM's bands, linear in between.
_FACTOR_ANCHORS: tuple[tuple[int, float], ...] = (
    (1, 0.55), (5, 0.70), (9, 0.82), (12, 0.90), (15, 0.96), (18, 0.99), (20, 1.00),
)


def _check(value: int) -> None:
    if not MIN_FAMILIARITY <= value <= MAX_FAMILIARITY:
        raise ValueError(f"familiarity {value} outside {MIN_FAMILIARITY}-{MAX_FAMILIARITY}")


def band_for(value: int) -> FamiliarityBand:
    _check(value)
    return next(band for floor, band in _BAND_FLOORS if value >= floor)


def familiarity_factor(value: int) -> float:
    _check(value)
    for (lo, f_lo), (hi, f_hi) in zip(_FACTOR_ANCHORS, _FACTOR_ANCHORS[1:], strict=False):
        if lo <= value <= hi:
            return f_lo + (f_hi - f_lo) * (value - lo) / (hi - lo)
    raise AssertionError("unreachable")


class PositionFamiliarity(Mapping[Position, int]):
    """Immutable familiarity per FM position. Unlisted positions are 1 (Ineffectual)."""

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[Position, int] | None = None) -> None:
        full = dict.fromkeys(Position, MIN_FAMILIARITY)
        for pos, value in (values or {}).items():
            _check(value)
            full[Position(pos)] = value
        self._values: dict[Position, int] = full

    def __getitem__(self, position: Position) -> int:
        return self._values[position]

    def __iter__(self) -> Iterator[Position]:
        return iter(Position)

    def __len__(self) -> int:
        return len(self._values)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PositionFamiliarity):
            return NotImplemented
        return self._values == other._values

    def __hash__(self) -> int:
        return hash(tuple(self._values[p] for p in Position))

    def __repr__(self) -> str:
        listed = {p.value: v for p, v in self._values.items() if v > MIN_FAMILIARITY}
        return f"PositionFamiliarity({listed})"

    def natural_positions(self) -> tuple[Position, ...]:
        """Positions with familiarity >= 15, in FM order."""
        return tuple(p for p in Position if self._values[p] >= NATURAL_THRESHOLD)
