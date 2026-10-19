"""Owner corrections (spec 011 R5, FR-012/FR-013): `corrections.csv` in the private repository,
append-only, one row per change. They are applied last, on the written 001 tables, by column
name, so any player, club, squad, attribute or position field can be corrected and the game's own
validator checks the result. The file itself is the field-level audit trail.

On a re-import a correction is never dropped: one whose source value changed under it, or whose
record is gone, is kept and reported.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from manager_core.domain.dataset import FlagKind, RecordType
from manager_core.io.dialect import DELIMITER, read_table, write_table

COLUMNS = ("record_type", "record_id", "field", "old_value", "new_value", "date", "note")
FILES = {
    RecordType.PLAYER.value: ("players.csv", "attributes.csv", "positions.csv", "squads.csv"),
    RecordType.CLUB.value: ("clubs.csv",),
}
KEYS = {RecordType.PLAYER.value: "player_id", RecordType.CLUB.value: "club_id"}


@dataclass(frozen=True, slots=True)
class Correction:
    record_type: str
    record_id: str
    field: str
    old_value: str
    new_value: str
    date: str
    note: str = ""


@dataclass
class Applied:
    applied: int = 0
    notes: list[str] = field(default_factory=list)  # for the import report
    edited: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # record -> fields


def read(path: Path) -> list[Correction]:
    if not path.exists():
        return []
    table = read_table(path)
    return [Correction(*(row.values.get(c, "") for c in COLUMNS)) for row in table.rows]


def append(path: Path, correction: Correction) -> None:
    """One more row; the file is created with its header (and a BOM, for pt-BR Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator="\n")
    new = not path.exists() or path.stat().st_size == 0
    if new:
        writer.writerow(COLUMNS)
    writer.writerow([getattr(correction, c) for c in COLUMNS])
    data = buffer.getvalue().encode("utf-8")
    if not new and not path.read_bytes().endswith(b"\n"):
        data = b"\n" + data
    with path.open("ab") as handle:
        handle.write((b"\xef\xbb\xbf" if new else b"") + data)


def file_for(record_type: str, field_name: str, dataset: Path) -> str | None:
    """The 001 file holding this field for this kind of record, if any."""
    for name in FILES.get(record_type, ()):
        columns = read_table(dataset / name).columns
        if field_name in columns and field_name != KEYS[record_type]:
            return name
    return None


def current_value(dataset: Path, record_type: str, record_id: str,
                  field_name: str) -> str | None:
    """The field's value in a written dataset; None when the record or field is not there."""
    name = file_for(record_type, field_name, dataset)
    if name is None:
        return None
    for row in read_table(dataset / name).rows:
        if row.values[KEYS[record_type]] == record_id:
            return row.values[field_name]
    return None


def apply(dataset: Path, corrections: list[Correction]) -> Applied:
    """Apply in file order (a later row wins) to the tables written in `dataset`."""
    result = Applied()
    tables: dict[str, tuple[tuple[str, ...], list[dict[str, str]]]] = {}

    def load(name: str) -> tuple[tuple[str, ...], list[dict[str, str]]]:
        if name not in tables:
            table = read_table(dataset / name)
            tables[name] = (table.columns, [dict(r.values) for r in table.rows])
        return tables[name]

    for c in corrections:
        label = f"{c.record_type}:{c.record_id} {c.field}"
        name = file_for(c.record_type, c.field, dataset)
        if name is None:
            result.notes.append(f"{label}: no such field, kept but not applied")
            continue
        _columns, rows = load(name)
        key = KEYS[c.record_type]
        row = next((r for r in rows if r[key] == c.record_id), None)
        if row is None:
            result.notes.append(f"{label}: the record is gone from the sources, kept")
            continue
        if row[c.field] not in (c.old_value, c.new_value):
            result.notes.append(f"{label}: source changed under a correction (was "
                                f"{c.old_value!r}, now {row[c.field]!r}); kept {c.new_value!r}")
        row[c.field] = c.new_value
        result.applied += 1
        fields = result.edited.setdefault((c.record_type, c.record_id), [])
        if c.field not in fields:
            fields.append(c.field)

    flags = load("record_flags.csv")[1]
    for (record_type, record_id), fields in sorted(result.edited.items()):
        flags.append({"record_type": record_type, "record_id": record_id,
                      "flag": FlagKind.MANUALLY_EDITED.value, "detail": ", ".join(fields)})
    for name, (columns, rows) in tables.items():
        write_table(dataset / name, columns, [[r[c] for c in columns] for r in rows])
    return result
