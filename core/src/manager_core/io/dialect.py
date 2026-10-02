"""Canonical CSV dialect (research R4, contracts/csv-format.md).

Write: UTF-8 with BOM, `;`, LF, rows sorted by key -> byte-stable output that opens directly
in pt-BR Excel. Read: canonical files only (BOM optional, LF or CRLF, trimmed cells).
Tolerance for files re-saved by Excel is spec 011.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DELIMITER = ";"
LIST_SEPARATOR = "|"


class DialectError(Exception):
    def __init__(self, code: str, path: Path | None, detail: str) -> None:
        super().__init__(f"{code}: {path}: {detail}")
        self.code = code
        self.path = path
        self.detail = detail


@dataclass(frozen=True, slots=True)
class Row:
    number: int  # spreadsheet row number: the header is row 1
    values: dict[str, str]


@dataclass(frozen=True, slots=True)
class Table:
    columns: tuple[str, ...]
    rows: list[Row]


def format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple | list):
        return LIST_SEPARATOR.join(format_value(v) for v in value)
    return str(value)


def write_table(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Sequence[str]],
    key_columns: int | None = None,
) -> None:
    """Write rows sorted by their first `key_columns` cells (default: the whole row)."""
    width = key_columns if key_columns is not None else len(columns)
    ordered = sorted((list(r) for r in rows), key=lambda r: r[:width])
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(ordered)
    path.write_bytes(b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8"))


def read_text_table(text: str) -> Table:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITER)
    lines = list(reader)
    if not lines:
        return Table((), [])
    columns = tuple(c.strip() for c in lines[0])
    rows: list[Row] = []
    for number, cells in enumerate(lines[1:], start=2):
        if not any(c.strip() for c in cells):
            continue
        padded = [c.strip() for c in cells] + [""] * (len(columns) - len(cells))
        rows.append(Row(number, dict(zip(columns, padded, strict=False))))
    return Table(columns, rows)


def read_table(path: Path) -> Table:
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DialectError("E033", path, f"not valid UTF-8 at byte {exc.start}") from exc
    return read_text_table(text)
