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
    number: int  # first physical line of the record (the header is line 1)
    values: dict[str, str]
    extra: tuple[str, ...] = ()  # cells beyond the header width (reported as E026)


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
    """Parse a canonical table. Row numbers come from the reader's physical line counter, so they
    stay right when a quoted cell spans several lines. Nothing is dropped silently: cells beyond
    the header are kept in `Row.extra` for validation to report."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITER)
    columns: tuple[str, ...] | None = None
    rows: list[Row] = []
    previous_line = 0
    for cells in reader:
        first_line = previous_line + 1
        previous_line = reader.line_num
        stripped = [c.strip() for c in cells]
        if columns is None:
            columns = tuple(stripped)
            continue
        if not any(stripped):
            continue
        width = len(columns)
        padded = stripped[:width] + [""] * (width - len(stripped[:width]))
        values = dict(zip(columns, padded, strict=True))
        rows.append(Row(first_line, values, tuple(stripped[width:])))
    return Table(columns or (), rows)


def read_table(path: Path) -> Table:
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DialectError("E033", path, f"not valid UTF-8 at byte {exc.start}") from exc
    return read_text_table(text)
