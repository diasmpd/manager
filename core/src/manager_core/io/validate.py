"""Import validation (FR-019/020): checks raw CSV tables BEFORE any domain object is built,
collecting every issue in one pass with its location.

This module holds the structural, schema-driven checks (E001, E002, E003, E004, E005, E010,
E025, W007). Cross-record rules from the data-model catalogue are added in US3.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from manager_core.domain.club import SLUG
from manager_core.i18n import t
from manager_core.io.dialect import LIST_SEPARATOR, Row, Table
from manager_core.io.schema import FILES, ColumnSpec, FileSpec, Kind

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT = re.compile(r"^-?\d+$")
_ID_COLUMNS = {"clubs.csv": "club_id", "players.csv": "player_id"}


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    severity: Severity
    file: str
    record_id: str | None
    row: int | None
    field: str | None
    value: str | None
    message: str

    @property
    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.file, self.row or 0, self.field or "", self.code)


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    def add(
        self,
        code: str,
        file: str,
        /,
        *,
        row: Row | None = None,
        record_id: str | None = None,
        field: str | None = None,
        value: str | None = None,
        **params: object,
    ) -> None:
        severity = Severity.WARNING if code.startswith("W") else Severity.ERROR
        self.issues.append(
            Issue(
                code=code,
                severity=severity,
                file=file,
                record_id=record_id,
                row=row.number if row else None,
                field=field,
                value=value,
                message=t(f"issue.{code}", **params),
            )
        )

    def extend(self, other: ValidationReport) -> None:
        self.issues.extend(other.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def sorted(self) -> ValidationReport:
        return ValidationReport(sorted(self.issues, key=lambda i: i.sort_key))


# ---- typed parsing, shared with the reader -------------------------------------------------


def parse_int(raw: str) -> int:
    if not _INT.match(raw):
        raise ValueError(raw)
    return int(raw)


def parse_date(raw: str) -> date:
    if not _ISO_DATE.match(raw):
        raise ValueError(raw)
    return date.fromisoformat(raw)


def parse_bool(raw: str) -> bool:
    lowered = raw.lower()
    if lowered not in ("true", "false"):
        raise ValueError(raw)
    return lowered == "true"


def parse_list(raw: str) -> tuple[str, ...]:
    items = tuple(part.strip() for part in raw.split(LIST_SEPARATOR))
    if any(not part for part in items):
        raise ValueError(raw)
    return items


def record_id_of(spec: FileSpec, row: Row) -> str:
    return " / ".join(row.values.get(k, "") for k in spec.key)


def _range_text(col: ColumnSpec) -> str:
    lo = "" if col.min is None else str(col.min)
    hi = "" if col.max is None else str(col.max)
    return f"{lo}–{hi}" if hi else f"≥ {lo}"


def _cell_error(
    report: ValidationReport, spec: FileSpec, col: ColumnSpec, row: Row, raw: str
) -> None:
    params: dict[str, object]
    if col.kind is Kind.INT:
        code, params = "E004", {"range": _range_text(col)}
    elif col.kind is Kind.DATE:
        code, params = "E010", {}
    else:
        code, params = "E005", {"max_len": col.max_len or "-"}
    report.add(
        code, spec.name, row=row, record_id=record_id_of(spec, row), field=col.name, value=raw,
        **params,
    )


def _check_cell(report: ValidationReport, spec: FileSpec, col: ColumnSpec, row: Row) -> None:
    raw = row.values.get(col.name, "")
    if raw == "":
        if col.required:
            _cell_error(report, spec, col, row, raw)
        return
    try:
        if col.kind is Kind.INT:
            value = parse_int(raw)
            too_low = col.min is not None and value < col.min
            too_high = col.max is not None and value > col.max
            if too_low or too_high:
                raise ValueError(raw)
        elif col.kind is Kind.DATE:
            parse_date(raw)
        elif col.kind is Kind.BOOL:
            parse_bool(raw)
        elif col.kind is Kind.LIST:
            parse_list(raw)
        elif col.max_len is not None and len(raw) > col.max_len:
            raise ValueError(raw)
    except ValueError:
        _cell_error(report, spec, col, row, raw)


def check_structure(tables: Mapping[str, Table | None]) -> ValidationReport:
    """Schema-driven checks on every present table; E001 for missing required files."""
    report = ValidationReport()
    for name, spec in FILES.items():
        table = tables.get(name)
        if table is None:
            if spec.required:
                report.add("E001", name)
            continue
        present = set(table.columns)
        for col_name in sorted({c for c in table.columns if table.columns.count(c) > 1}):
            report.add("E028", name, field=col_name)
        for row in table.rows:
            if row.extra:
                report.add("E026", name, row=row, record_id=record_id_of(spec, row),
                           value=";".join(row.extra), count=len(row.extra))
        missing = {c.name for c in spec.columns if c.required and c.name not in present}
        for col_name in sorted(missing):
            report.add("E025", name, field=col_name)
        for col_name in table.columns:
            if col_name not in spec.names:
                report.add("W007", name, field=col_name)
        checked = [c for c in spec.columns if c.name not in missing]
        id_column = _ID_COLUMNS.get(name)
        seen: dict[str, int] = {}
        for row in table.rows:
            for col in checked:
                _check_cell(report, spec, col, row)
            if id_column and id_column not in missing:
                rid = row.values.get(id_column, "")
                if rid and not SLUG.match(rid):
                    report.add("E002", name, row=row, record_id=rid, field=id_column, value=rid)
                if rid in seen:
                    report.add("E003", name, row=row, record_id=rid, field=id_column, value=rid)
                seen.setdefault(rid, row.number)
    return report
