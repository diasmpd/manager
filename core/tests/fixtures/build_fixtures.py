"""Builds the import test fixtures (tasks T045, T046, T048) reproducibly.

Run from core/:  python tests/fixtures/build_fixtures.py
Outputs are committed. Each invalid fixture is `valid/minimal` plus exactly one defect, with an
`expected.txt` (code;file;record_id;field) naming the issue the importer must report.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path

from manager_core.domain.attributes import ALL_ATTRIBUTES, HIDDEN_ATTRIBUTES, Attributes
from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset, Source
from manager_core.domain.player import Player
from manager_core.domain.positions import Position, PositionFamiliarity
from manager_core.domain.squad import SquadMembership
from manager_core.io.dialect import read_table, write_table
from manager_core.io.writer import write
from manager_core.ratings.suitability import position_weights

ROOT = Path(__file__).resolve().parent
MINIMAL = ROOT / "valid" / "minimal"
SHAPE = (Position.GK, Position.GK, Position.DC, Position.DC, Position.DL, Position.DR,
         Position.DM, Position.MC, Position.MC, Position.AMC, Position.ST, Position.ST)


def _attributes(position: Position) -> Attributes:
    values = dict.fromkeys(ALL_ATTRIBUTES, 9)
    for name in position_weights()[position]:
        values[name] = 14
    if position is not Position.GK:
        values.update({n: 2 for n in ("aerial_reach", "command_of_area", "communication",
                                      "eccentricity", "handling", "kicking", "one_on_ones",
                                      "punching", "reflexes", "rushing_out", "throwing")})
    values.update(consistency=12, temperament=7, dirtiness=8)  # not all hidden equal (W005)
    return Attributes(**values)


def _player(pid: str, position: Position, born: date, pa: int = 150) -> Player:
    return Player(
        id=pid, full_name=f"Jogador {pid.upper()}", display_name=f"J{pid[-3:]}",
        date_of_birth=born, nationalities=("BRA",), height_cm=180, weight_kg=76,
        left_foot=8, right_foot=20, attributes=_attributes(position),
        positions=PositionFamiliarity({position: 20}), potential_ability=pa,
    )


def build_minimal() -> None:
    clubs = {
        "clube-a": Club("clube-a", "Clube Teste A", "Teste A", "TSA", "Cidade A", "MG", "BRA",
                        "#112233", "#FFFFFF", "Estádio A", 10000, 1950, 10),
        "clube-b": Club("clube-b", "Club Prueba B", "Prueba B", "PRB", "Rosario", None, "ARG",
                        "#AA0000", "#000000", "Estadio B", 20000, 1930, 11),
    }
    players: dict[str, Player] = {}
    memberships: dict[str, SquadMembership] = {}
    for prefix, club in (("a", "clube-a"), ("b", "clube-b")):
        for i, position in enumerate(SHAPE, start=1):
            pid = f"p-{prefix}{i:02d}"
            pa = 40 if pid == "p-a12" else 150  # p-a12: PA below CA -> W010 + potential_raised
            players[pid] = _player(pid, position, date(1995 + i % 8, 1 + i % 12, 10), pa)
            memberships[pid] = SquadMembership(pid, club, shirt_number=i)
    players["p-fa01"] = _player("p-fa01", Position.MC, date(1999, 3, 3))  # free agent
    dataset = Dataset(
        format_version="1.0", reference_date=date(2027, 1, 1), fictional=True,
        tool="tests.fixtures.build_fixtures", tool_version="1", seed=None,
        notes="Fixture mínima para testes de importação.",
        sources=(Source("Fixture escrita à mão", date(2026, 10, 2)),),
        clubs=clubs, players=players, memberships=memberships,
    )
    if MINIMAL.exists():
        shutil.rmtree(MINIMAL)
    write(dataset, MINIMAL)
    # p-b12 has no hidden attributes at all (as public sources) -> hidden_defaulted
    _edit_cells(MINIMAL, "attributes.csv", "p-b12", dict.fromkeys(HIDDEN_ATTRIBUTES, ""))


# ---- small CSV editing helpers --------------------------------------------------------------


def _load(folder: Path, name: str) -> tuple[list[str], list[dict[str, str]]]:
    table = read_table(folder / name)
    return list(table.columns), [dict(r.values) for r in table.rows]


def _save(folder: Path, name: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    write_table(folder / name, columns, [[r.get(c, "") for c in columns] for r in rows])


def _edit_cells(folder: Path, name: str, record_id: str, changes: dict[str, str]) -> None:
    columns, rows = _load(folder, name)
    key = columns[0]
    for row in rows:
        if row[key] == record_id:
            row.update(changes)
    _save(folder, name, columns, rows)


def _drop_rows(folder: Path, name: str, record_ids: set[str]) -> None:
    columns, rows = _load(folder, name)
    _save(folder, name, columns, [r for r in rows if r[columns[0]] not in record_ids])


def _append_row(folder: Path, name: str, row: dict[str, str]) -> None:
    columns, rows = _load(folder, name)
    _save(folder, name, columns, [*rows, row])


def _drop_column(folder: Path, name: str, column: str) -> None:
    columns, rows = _load(folder, name)
    _save(folder, name, [c for c in columns if c != column], rows)


def _copy_row(folder: Path, name: str, record_id: str) -> dict[str, str]:
    columns, rows = _load(folder, name)
    return dict(next(r for r in rows if r[columns[0]] == record_id))


# ---- invalid fixtures: (folder name, defect, expected code;file;record_id;field) -----------

Defect = Callable[[Path], None]


def _no_positions(d: Path) -> None:
    _edit_cells(d, "positions.csv", "p-a03", {p.value: "" for p in Position} | {"DC": "12"})


def _cp1252(d: Path) -> None:
    (d / "clubs.csv").write_bytes("club_id;name\nclube-a;Clube São Paulo\n".encode("cp1252"))


def _dup_membership(d: Path) -> None:
    _append_row(d, "squads.csv", {"player_id": "p-a03", "club_id": "clube-b", "shirt_number": "40"})


def _dup_player(d: Path) -> None:
    _append_row(d, "players.csv", _copy_row(d, "players.csv", "p-a03"))


INVALID: list[tuple[str, Defect, str]] = [
    ("E001_missing_file", lambda d: (d / "clubs.csv").unlink(), "E001;clubs.csv;;"),
    ("E002_bad_id", lambda d: _edit_cells(d, "clubs.csv", "clube-b", {"club_id": "Clube B"}),
     "E002;clubs.csv;Clube B;club_id"),
    ("E003_duplicate_id", _dup_player, "E003;players.csv;p-a03;player_id"),
    ("E004_attribute_out_of_range",
     lambda d: _edit_cells(d, "attributes.csv", "p-a11", {"finishing": "23"}),
     "E004;attributes.csv;p-a11;finishing"),
    ("E005_text_too_long",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"display_name": "X" * 31}),
     "E005;players.csv;p-a03;display_name"),
    ("E010_bad_date",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"date_of_birth": "2001-13-40"}),
     "E010;players.csv;p-a03;date_of_birth"),
    ("E011_age_out_of_range",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"date_of_birth": "1970-01-01"}),
     "E011;players.csv;p-a03;date_of_birth"),
    ("E013_bad_nation",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"nationalities": "Brasil"}),
     "E013;players.csv;p-a03;nationalities"),
    ("E014_no_good_foot",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"left_foot": "10", "right_foot": "11"}),
     "E014;players.csv;p-a03;right_foot"),
    ("E016_no_position", _no_positions, "E016;positions.csv;p-a03;positions"),
    ("E017_unknown_club",
     lambda d: _edit_cells(d, "squads.csv", "p-a03", {"club_id": "clube-z"}),
     "E017;squads.csv;p-a03;club_id"),
    ("E018_duplicate_membership", _dup_membership, "E018;squads.csv;p-a03;player_id"),
    ("E019_duplicate_shirt",
     lambda d: _edit_cells(d, "squads.csv", "p-a03", {"shirt_number": "4"}),
     "E019;squads.csv;p-a04;shirt_number"),
    ("E020_bad_abbreviation",
     lambda d: _edit_cells(d, "clubs.csv", "clube-a", {"abbreviation": "Ta1"}),
     "E020;clubs.csv;clube-a;abbreviation"),
    ("E021_bad_uf", lambda d: _edit_cells(d, "clubs.csv", "clube-a", {"state": "XX"}),
     "E021;clubs.csv;clube-a;state"),
    ("E022_bad_colour", lambda d: _edit_cells(d, "clubs.csv", "clube-a", {"color_primary": "red"}),
     "E022;clubs.csv;clube-a;color_primary"),
    ("E023_missing_currency",
     lambda d: _edit_cells(d, "squads.csv", "p-a03", {"market_value": "1000000"}),
     "E023;squads.csv;p-a03;currency"),
    ("E024_missing_attributes", lambda d: _drop_rows(d, "attributes.csv", {"p-a03"}),
     "E024;attributes.csv;p-a03;player_id"),
    ("E025_missing_column", lambda d: _drop_column(d, "attributes.csv", "finishing"),
     "E025;attributes.csv;;finishing"),
    ("E030_bad_version",
     lambda d: _edit_cells(d, "dataset.csv", "1.0", {"format_version": "abc"}),
     "E030;dataset.csv;;format_version"),
    ("E031_newer_version",
     lambda d: _edit_cells(d, "dataset.csv", "1.0", {"format_version": "2.0"}),
     "E031;dataset.csv;;format_version"),
    ("E032_no_source", lambda d: _save(d, "sources.csv", _load(d, "sources.csv")[0], []),
     "E032;sources.csv;;"),
    ("E033_not_utf8", _cp1252, "E033;clubs.csv;;"),
]


def _multi(d: Path) -> None:
    _edit_cells(d, "attributes.csv", "p-a11", {"finishing": "23"})
    _edit_cells(d, "players.csv", "p-a05", {"date_of_birth": "2001-13-40"})
    _edit_cells(d, "clubs.csv", "clube-b", {"stadium_capacity": "10"})


MULTI_EXPECTED = [
    "E004;attributes.csv;p-a11;finishing",
    "E010;players.csv;p-a05;date_of_birth",
    "E004;clubs.csv;clube-b;stadium_capacity",
]


def _club_too_small(d: Path) -> None:
    gone = {f"p-b{i:02d}" for i in range(3, 6)}
    for name in ("players.csv", "attributes.csv", "positions.csv", "squads.csv"):
        _drop_rows(d, name, gone)


WARNINGS: list[tuple[str, Defect, str]] = [
    ("W001_club_not_playable", _club_too_small, "W001;clubs.csv;clube-b;club_id"),
    ("W002_outfield_keeper_attrs",
     lambda d: _edit_cells(d, "attributes.csv", "p-a03", {"reflexes": "18"}),
     "W002;attributes.csv;p-a03;goalkeeping"),
    ("W003_keeper_finishing",
     lambda d: _edit_cells(d, "attributes.csv", "p-a01", {"finishing": "15"}),
     "W003;attributes.csv;p-a01;finishing"),
    ("W004_old_and_fast", lambda d: (
        _edit_cells(d, "players.csv", "p-a03", {"date_of_birth": "1990-01-01"}),
        _edit_cells(d, "attributes.csv", "p-a03", {"pace": "18"}))[-1],
     "W004;attributes.csv;p-a03;pace"),
    ("W005_hidden_all_equal",
     lambda d: _edit_cells(d, "attributes.csv", "p-a03", dict.fromkeys(HIDDEN_ATTRIBUTES, "10")),
     "W005;attributes.csv;p-a03;hidden"),
    ("W006_unknown_nation",
     lambda d: _edit_cells(d, "players.csv", "p-a03", {"nationalities": "BRA|XYZ"}),
     "W006;players.csv;p-a03;nationalities"),
    ("W007_unknown_column", lambda d: _save(
        d, "clubs.csv", [*_load(d, "clubs.csv")[0], "mascote"], _load(d, "clubs.csv")[1]),
     "W007;clubs.csv;;mascote"),
]


def _build_variants(base: Path, variants: list[tuple[str, Defect, str]]) -> None:
    if base.exists():
        shutil.rmtree(base)
    for name, defect, expected in variants:
        target = base / name
        shutil.copytree(MINIMAL, target)
        defect(target)
        (target / "expected.txt").write_text(expected + "\n", encoding="utf-8")


def main() -> None:
    build_minimal()
    _build_variants(ROOT / "invalid", [*INVALID, ("multi_3_defects", _multi, "")])
    (ROOT / "invalid" / "multi_3_defects" / "expected.txt").write_text(
        "\n".join(MULTI_EXPECTED) + "\n", encoding="utf-8"
    )
    _build_variants(ROOT / "warnings", WARNINGS)


if __name__ == "__main__":
    main()
