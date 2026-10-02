"""Cross-record validation rules (data-model.md catalogue). Run only on structurally valid
tables (validate.check_structure passed), so required cells exist and parse.

Linear in the number of records: every lookup goes through dicts/sets built once.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from functools import cache
from importlib import resources

from manager_core.domain.attributes import ATTRIBUTE_GROUPS, HIDDEN_ATTRIBUTES, AttributeGroup
from manager_core.domain.dataset import FlagKind, RecordType
from manager_core.domain.positions import NATURAL_THRESHOLD, Position
from manager_core.i18n import t
from manager_core.io.dialect import Row, Table, read_text_table
from manager_core.io.schema import SUPPORTED_MAJOR
from manager_core.io.validate import ValidationReport, parse_date, parse_int, parse_list

UF_CODES = frozenset({
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
})
_NATION = re.compile(r"^[A-Z]{3}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_ABBREVIATION = re.compile(r"^[A-Z]{3}$")
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_VERSION = re.compile(r"^(\d+)\.(\d+)$")
_GK_ATTRS = ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]


@cache
def known_nations() -> frozenset[str]:
    text = resources.files("manager_core.reference").joinpath("nations.csv").read_text("utf-8-sig")
    return frozenset(r.values["code"] for r in read_text_table(text).rows)


def _rows(tables: Mapping[str, Table | None], name: str) -> list[Row]:
    table = tables.get(name)
    return table.rows if table else []


def _age(born: date, on: date) -> int:
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def _check_nation(report: ValidationReport, file: str, row: Row, rid: str, field: str,
                  code: str) -> None:
    if not _NATION.match(code):
        report.add("E013", file, row=row, record_id=rid, field=field, value=code)
    elif code not in known_nations():
        report.add("W006", file, row=row, record_id=rid, field=field, value=code, nation=code)


def check_rules(tables: Mapping[str, Table | None]) -> ValidationReport:
    report = ValidationReport()

    # ---- dataset.csv / sources.csv ---------------------------------------------------------
    meta_rows = _rows(tables, "dataset.csv")
    reference: date | None = None
    if len(meta_rows) != 1:
        report.add("E005", "dataset.csv", field="format_version", max_len="-")
    else:
        meta = meta_rows[0]
        version = meta.values["format_version"]
        match = _VERSION.match(version)
        if not match or int(match.group(1)) < SUPPORTED_MAJOR:
            report.add("E030", "dataset.csv", row=meta, field="format_version", value=version,
                       version=version)
        elif int(match.group(1)) > SUPPORTED_MAJOR:
            report.add("E031", "dataset.csv", row=meta, field="format_version", value=version,
                       version=version, supported=SUPPORTED_MAJOR)
        reference = parse_date(meta.values["reference_date"])
    if not _rows(tables, "sources.csv"):
        report.add("E032", "sources.csv")

    # ---- clubs.csv -------------------------------------------------------------------------
    club_ids: set[str] = set()
    for row in _rows(tables, "clubs.csv"):
        v = row.values
        cid = v["club_id"]
        club_ids.add(cid)
        if not _ABBREVIATION.match(v["abbreviation"]):
            report.add("E020", "clubs.csv", row=row, record_id=cid, field="abbreviation",
                       value=v["abbreviation"])
        for field in ("color_primary", "color_secondary"):
            if not _COLOUR.match(v[field]):
                report.add("E022", "clubs.csv", row=row, record_id=cid, field=field, value=v[field])
        _check_nation(report, "clubs.csv", row, cid, "country", v["country"])
        if v["country"] == "BRA" and v.get("state", "") not in UF_CODES:
            report.add("E021", "clubs.csv", row=row, record_id=cid, field="state",
                       value=v.get("state", ""))
        if reference and parse_int(v["founded_year"]) > reference.year:
            report.add("E004", "clubs.csv", row=row, record_id=cid, field="founded_year",
                       value=v["founded_year"], range=f"1850–{reference.year}")

    # ---- players.csv -----------------------------------------------------------------------
    player_rows = {r.values["player_id"]: r for r in _rows(tables, "players.csv")}
    ages: dict[str, int] = {}
    for pid, row in player_rows.items():
        v = row.values
        for code in parse_list(v["nationalities"]):
            _check_nation(report, "players.csv", row, pid, "nationalities", code)
        if len(parse_list(v["nationalities"])) > 3:
            report.add("E005", "players.csv", row=row, record_id=pid, field="nationalities",
                       value=v["nationalities"], max_len=3)
        if reference:
            age = _age(parse_date(v["date_of_birth"]), reference)
            ages[pid] = age
            if not 14 <= age <= 45:
                report.add("E011", "players.csv", row=row, record_id=pid, field="date_of_birth",
                           value=v["date_of_birth"], age=age)
        if max(parse_int(v["left_foot"]), parse_int(v["right_foot"])) < 15:
            report.add("E014", "players.csv", row=row, record_id=pid, field="right_foot",
                       value=f"{v['left_foot']}/{v['right_foot']}")

    # ---- attributes.csv / positions.csv coverage (E024) ------------------------------------
    covered: dict[str, dict[str, Row]] = {}
    for name in ("attributes.csv", "positions.csv"):
        seen: dict[str, Row] = {}
        for row in _rows(tables, name):
            pid = row.values.get("player_id", "")
            if pid not in player_rows or pid in seen:
                report.add("E024", name, row=row, record_id=pid, field="player_id", value=pid,
                           file=name)
            seen.setdefault(pid, row)
        for pid in sorted(set(player_rows) - set(seen)):
            report.add("E024", name, record_id=pid, field="player_id", value=pid, file=name)
        covered[name] = seen

    # ---- positions (E016) and goalkeeper detection ------------------------------------------
    goalkeepers: set[str] = set()
    for pid, row in covered["positions.csv"].items():
        values = {p: parse_int(row.values[p.value]) for p in Position if row.values.get(p.value)}
        if not any(v >= NATURAL_THRESHOLD for v in values.values()):
            report.add("E016", "positions.csv", row=row, record_id=pid, field="positions")
        if values.get(Position.GK, 1) >= NATURAL_THRESHOLD:
            goalkeepers.add(pid)

    # ---- attribute plausibility warnings (W002-W005) -----------------------------------------
    for pid, row in covered["attributes.csv"].items():
        v = row.values
        if pid in goalkeepers:
            if parse_int(v["finishing"]) > 12 or parse_int(v["dribbling"]) > 12:
                report.add("W003", "attributes.csv", row=row, record_id=pid, field="finishing")
        elif any(parse_int(v[n]) > 10 for n in _GK_ATTRS):
            report.add("W002", "attributes.csv", row=row, record_id=pid, field="goalkeeping")
        if ages.get(pid, 0) >= 34 and max(parse_int(v["pace"]), parse_int(v["acceleration"])) >= 17:
            report.add("W004", "attributes.csv", row=row, record_id=pid, field="pace")
        hidden = [v.get(n, "") for n in HIDDEN_ATTRIBUTES]
        if all(hidden) and len(set(hidden)) == 1:
            report.add("W005", "attributes.csv", row=row, record_id=pid, field="hidden")

    # ---- squads.csv (E017, E018, E019, E023) and W001 ---------------------------------------
    members: dict[str, set[str]] = {cid: set() for cid in club_ids}
    numbers: dict[tuple[str, int], str] = {}
    seen_players: set[str] = set()
    for row in _rows(tables, "squads.csv"):
        v = row.values
        pid, cid = v["player_id"], v["club_id"]
        if pid not in player_rows:
            report.add("E017", "squads.csv", row=row, record_id=pid, field="player_id", value=pid,
                       kind=t("kind.player"), ref=pid)
        if cid not in club_ids:
            report.add("E017", "squads.csv", row=row, record_id=pid, field="club_id", value=cid,
                       kind=t("kind.club"), ref=cid)
        if pid in seen_players:
            report.add("E018", "squads.csv", row=row, record_id=pid, field="player_id", value=pid)
        seen_players.add(pid)
        if cid in members and pid in player_rows:
            members[cid].add(pid)
        if v.get("shirt_number"):
            key = (cid, parse_int(v["shirt_number"]))
            if key in numbers:
                report.add("E019", "squads.csv", row=row, record_id=pid, field="shirt_number",
                           value=v["shirt_number"], number=key[1], club=cid)
            numbers.setdefault(key, pid)
        money = v.get("market_value") or v.get("wage_monthly")
        currency = v.get("currency", "")
        if (money and not currency) or (currency and not _CURRENCY.match(currency)):
            report.add("E023", "squads.csv", row=row, record_id=pid, field="currency",
                       value=currency)
    for cid in sorted(members):
        squad = members[cid]
        if len(squad) < 11 or not squad & goalkeepers:
            report.add("W001", "clubs.csv", record_id=cid, field="club_id", value=cid)

    # ---- external_refs.csv / record_flags.csv ------------------------------------------------
    known = {RecordType.CLUB.value: club_ids, RecordType.PLAYER.value: set(player_rows)}
    for name, extra in (("external_refs.csv", None), ("record_flags.csv", "flag")):
        for row in _rows(tables, name):
            v = row.values
            rtype, rid = v["record_type"], v["record_id"]
            if rtype not in known:
                report.add("E005", name, row=row, record_id=rid, field="record_type", value=rtype,
                           max_len="-")
            elif rid not in known[rtype]:
                report.add("E017", name, row=row, record_id=rid, field="record_id", value=rid,
                           kind=t(f"kind.{rtype}"), ref=rid)
            if extra and v[extra] not in {f.value for f in FlagKind}:
                report.add("E005", name, row=row, record_id=rid, field=extra, value=v[extra],
                           max_len="-")
    return report
