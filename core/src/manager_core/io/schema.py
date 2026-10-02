"""Dataset CSV format v1.0: file and column specs (contracts/csv-format.md).

The attributes.csv columns are generated from ATTRIBUTE_GROUPS (single source of truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from manager_core.domain.attributes import ALL_ATTRIBUTES, HIDDEN_ATTRIBUTES
from manager_core.domain.positions import Position

FORMAT_VERSION = "1.0"
SUPPORTED_MAJOR = 1


class Kind(StrEnum):
    STR = "str"
    INT = "int"
    DATE = "date"
    BOOL = "bool"
    LIST = "list"


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    name: str
    kind: Kind = Kind.STR
    required: bool = True
    min: int | None = None
    max: int | None = None
    max_len: int | None = None


@dataclass(frozen=True, slots=True)
class FileSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    key: tuple[str, ...]
    required: bool

    def column(self, name: str) -> ColumnSpec:
        return next(c for c in self.columns if c.name == name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)


def _s(name: str, required: bool = True, max_len: int | None = None) -> ColumnSpec:
    return ColumnSpec(name, Kind.STR, required, max_len=max_len)


def _i(name: str, lo: int | None, hi: int | None, required: bool = True) -> ColumnSpec:
    return ColumnSpec(name, Kind.INT, required, lo, hi)


def _d(name: str, required: bool = True) -> ColumnSpec:
    return ColumnSpec(name, Kind.DATE, required)


_FILES: tuple[FileSpec, ...] = (
    FileSpec(
        "dataset.csv",
        (
            _s("format_version"), _d("reference_date"), ColumnSpec("fictional", Kind.BOOL),
            _s("tool"), _s("tool_version"), _i("seed", 0, None, required=False),
            _s("notes", required=False),
        ),
        key=("format_version",),
        required=True,
    ),
    FileSpec(
        "sources.csv",
        (_s("name"), _s("url", False), _d("retrieved_on"), _s("licence_notes", False)),
        key=("name", "retrieved_on"),
        required=True,
    ),
    FileSpec(
        "clubs.csv",
        (
            _s("club_id"), _s("name", max_len=60), _s("short_name", max_len=20),
            _s("abbreviation"), _s("city", max_len=60), _s("state", False), _s("country"),
            _s("color_primary"), _s("color_secondary"), _s("stadium_name", max_len=80),
            _i("stadium_capacity", 500, 250_000), _i("founded_year", 1850, None),
            _i("reputation", 1, 20),
        ),
        key=("club_id",),
        required=True,
    ),
    FileSpec(
        "players.csv",
        (
            _s("player_id"), _s("full_name", max_len=80), _s("display_name", max_len=30),
            _d("date_of_birth"), ColumnSpec("nationalities", Kind.LIST),
            _i("height_cm", 150, 210), _i("weight_kg", 50, 110),
            _i("left_foot", 1, 20), _i("right_foot", 1, 20),
            _i("potential_ability", 1, 200, required=False),
        ),
        key=("player_id",),
        required=True,
    ),
    FileSpec(
        "attributes.csv",
        (
            _s("player_id"),
            *(_i(n, 1, 20, required=n not in HIDDEN_ATTRIBUTES) for n in ALL_ATTRIBUTES),
        ),
        key=("player_id",),
        required=True,
    ),
    FileSpec(
        "positions.csv",
        (_s("player_id"), *(_i(p.value, 1, 20, required=False) for p in Position)),
        key=("player_id",),
        required=True,
    ),
    FileSpec(
        "squads.csv",
        (
            _s("player_id"), _s("club_id"), _i("shirt_number", 1, 99, required=False),
            _i("market_value", 0, None, required=False),
            _i("wage_monthly", 0, None, required=False),
            _s("currency", False), _d("contract_expiry", required=False),
        ),
        key=("player_id",),
        required=False,
    ),
    FileSpec(
        "external_refs.csv",
        (_s("record_type"), _s("record_id"), _s("source"), _s("source_id")),
        key=("record_type", "record_id", "source", "source_id"),
        required=False,
    ),
    FileSpec(
        "record_flags.csv",
        (_s("record_type"), _s("record_id"), _s("flag"), _s("detail", False)),
        key=("record_type", "record_id", "flag"),
        required=False,
    ),
)

FILES: dict[str, FileSpec] = {f.name: f for f in _FILES}
