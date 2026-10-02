"""Dataset folder -> Dataset, all-or-nothing (FR-019).

Every table is read and validated first. Domain objects are only built when the report has
no errors. Hidden-attribute and potential defaults are applied here and recorded as
provenance flags.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path

from manager_core.domain.attributes import (
    ALL_ATTRIBUTES,
    ATTRIBUTE_GROUPS,
    HIDDEN_ATTRIBUTES,
    HIDDEN_DEFAULTS,
    AttributeGroup,
    Attributes,
)
from manager_core.domain.club import Club, ExternalRef
from manager_core.domain.dataset import Dataset, FlagKind, RecordFlag, RecordType, Source
from manager_core.domain.player import Player
from manager_core.domain.positions import Position, PositionFamiliarity
from manager_core.domain.squad import SquadMembership
from manager_core.io.dialect import DialectError, Row, Table, read_table
from manager_core.io.rules import check_rules
from manager_core.io.schema import FILES
from manager_core.io.validate import (
    ValidationReport,
    check_structure,
    parse_bool,
    parse_date,
    parse_int,
    parse_list,
)
from manager_core.ratings.ability import current_ability, is_goalkeeper


@dataclass(frozen=True, slots=True)
class LoadResult:
    report: ValidationReport
    dataset: Dataset | None


def _read_all(path: Path) -> tuple[dict[str, Table | None], ValidationReport]:
    report = ValidationReport()
    tables: dict[str, Table | None] = {}
    for name in FILES:
        file = path / name
        if not file.is_file():
            tables[name] = None
            continue
        try:
            tables[name] = read_table(file)
        except DialectError as exc:
            tables[name] = Table((), [])
            report.add(exc.code, name, detail=exc.detail)
    return tables, report


def load(path: Path) -> LoadResult:
    tables, report = _read_all(path)
    if report.ok:
        report.extend(check_structure(tables))
    if report.ok:
        report.extend(check_rules(tables))
    if not report.ok:
        return LoadResult(report.sorted(), None)
    dataset = _build(tables, report)
    return LoadResult(report.sorted(), dataset)


# ---- building (only reached with a clean report) -------------------------------------------


def _rows(tables: dict[str, Table | None], name: str) -> list[Row]:
    table = tables.get(name)
    return table.rows if table else []


def _opt_int(raw: str) -> int | None:
    return parse_int(raw) if raw else None


def _opt(raw: str) -> str | None:
    return raw or None


def _build(tables: dict[str, Table | None], report: ValidationReport) -> Dataset:
    meta = _rows(tables, "dataset.csv")[0].values
    reference_date = parse_date(meta["reference_date"])

    refs: dict[tuple[str, str], list[ExternalRef]] = {}
    for row in _rows(tables, "external_refs.csv"):
        v = row.values
        refs.setdefault((v["record_type"], v["record_id"]), []).append(
            ExternalRef(v["source"], v["source_id"])
        )

    def refs_for(kind: RecordType, rid: str) -> tuple[ExternalRef, ...]:
        found = refs.get((kind.value, rid), [])
        return tuple(sorted(found, key=lambda r: (r.source, r.source_id)))

    flags = [
        RecordFlag(
            RecordType(r.values["record_type"]),
            r.values["record_id"],
            FlagKind(r.values["flag"]),
            r.values.get("detail", ""),
        )
        for r in _rows(tables, "record_flags.csv")
    ]

    clubs: dict[str, Club] = {}
    for row in _rows(tables, "clubs.csv"):
        v = row.values
        clubs[v["club_id"]] = Club(
            id=v["club_id"],
            name=v["name"],
            short_name=v["short_name"],
            abbreviation=v["abbreviation"],
            city=v["city"],
            state=_opt(v.get("state", "")),
            country=v["country"],
            color_primary=v["color_primary"],
            color_secondary=v["color_secondary"],
            stadium_name=v["stadium_name"],
            stadium_capacity=parse_int(v["stadium_capacity"]),
            founded_year=parse_int(v["founded_year"]),
            reputation=parse_int(v["reputation"]),
            external_refs=refs_for(RecordType.CLUB, v["club_id"]),
        )

    attributes = {r.values["player_id"]: r for r in _rows(tables, "attributes.csv")}
    positions = {r.values["player_id"]: r for r in _rows(tables, "positions.csv")}

    players: dict[str, Player] = {}
    for row in _rows(tables, "players.csv"):
        v = row.values
        pid = v["player_id"]
        attr_row = attributes[pid].values
        values: dict[str, int] = {}
        defaulted = False
        for name in ALL_ATTRIBUTES:
            raw = attr_row.get(name, "")
            if raw == "" and name in HIDDEN_ATTRIBUTES:
                values[name] = HIDDEN_DEFAULTS[name]
                defaulted = True
            else:
                values[name] = parse_int(raw)
        if defaulted:
            flags.append(RecordFlag(RecordType.PLAYER, pid, FlagKind.HIDDEN_DEFAULTED))
        pos_row = positions[pid].values
        familiarity = {
            p: parse_int(pos_row[p.value]) for p in Position if pos_row.get(p.value, "")
        }
        player = Player(
            id=pid,
            full_name=v["full_name"],
            display_name=v["display_name"],
            date_of_birth=parse_date(v["date_of_birth"]),
            nationalities=parse_list(v["nationalities"]),
            height_cm=parse_int(v["height_cm"]),
            weight_kg=parse_int(v["weight_kg"]),
            left_foot=parse_int(v["left_foot"]),
            right_foot=parse_int(v["right_foot"]),
            attributes=Attributes(**values),
            positions=PositionFamiliarity(familiarity),
            potential_ability=200,  # provisional: final PA needs the derived CA
            external_refs=refs_for(RecordType.PLAYER, pid),
        )
        ca = current_ability(player)
        stated = _opt_int(v.get("potential_ability", ""))
        if stated is None:
            pa = ca
            flags.append(RecordFlag(RecordType.PLAYER, pid, FlagKind.POTENTIAL_DEFAULTED))
        elif stated < ca:
            pa = ca
            flags.append(
                RecordFlag(RecordType.PLAYER, pid, FlagKind.POTENTIAL_RAISED, f"{stated}->{ca}")
            )
            report.add(
                "W010", "players.csv", row=row, record_id=pid, field="potential_ability",
                value=str(stated), pa=stated, ca=ca,
            )
        else:
            pa = stated
        players[pid] = dataclasses.replace(player, potential_ability=pa)

    memberships: dict[str, SquadMembership] = {}
    for row in _rows(tables, "squads.csv"):
        v = row.values
        expiry = v.get("contract_expiry", "")
        memberships[v["player_id"]] = SquadMembership(
            player_id=v["player_id"],
            club_id=v["club_id"],
            shirt_number=_opt_int(v.get("shirt_number", "")),
            market_value=_opt_int(v.get("market_value", "")),
            wage_monthly=_opt_int(v.get("wage_monthly", "")),
            currency=_opt(v.get("currency", "")),
            contract_expiry=parse_date(expiry) if expiry else None,
        )

    _domain_warnings(report, tables, clubs, players, memberships)

    sources = tuple(
        Source(
            name=r.values["name"],
            retrieved_on=parse_date(r.values["retrieved_on"]),
            url=_opt(r.values.get("url", "")),
            licence_notes=_opt(r.values.get("licence_notes", "")),
        )
        for r in _rows(tables, "sources.csv")
    )

    return Dataset(
        format_version=meta["format_version"],
        reference_date=reference_date,
        fictional=parse_bool(meta["fictional"]),
        tool=meta["tool"],
        tool_version=meta["tool_version"],
        seed=_opt_int(meta.get("seed", "")),
        notes=meta.get("notes", ""),
        sources=sources,
        clubs=clubs,
        players=players,
        memberships=memberships,
        record_flags=tuple(flags),
    )


_GK_ATTRS = ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]


def _domain_warnings(
    report: ValidationReport,
    tables: dict[str, Table | None],
    clubs: dict[str, Club],
    players: dict[str, Player],
    memberships: dict[str, SquadMembership],
) -> None:
    """W001-W003: plausibility checks that need the domain's goalkeeper rule
    (best position = GK), so validation and gameplay agree on who is a goalkeeper."""
    keepers = {pid for pid, p in players.items() if is_goalkeeper(p)}
    attr_rows = {r.values["player_id"]: r for r in _rows(tables, "attributes.csv")}
    for pid in sorted(players):
        attrs, row = players[pid].attributes, attr_rows[pid]
        if pid in keepers:
            if attrs.finishing > 12 or attrs.dribbling > 12:
                report.add("W003", "attributes.csv", row=row, record_id=pid, field="finishing")
        elif any(attrs.get(n) > 10 for n in _GK_ATTRS):
            report.add("W002", "attributes.csv", row=row, record_id=pid, field="goalkeeping")
    club_rows = {r.values["club_id"]: r for r in _rows(tables, "clubs.csv")}
    squads: dict[str, set[str]] = {cid: set() for cid in clubs}
    for m in memberships.values():
        squads[m.club_id].add(m.player_id)
    for cid in sorted(squads):
        if len(squads[cid]) < 11 or not squads[cid] & keepers:
            report.add("W001", "clubs.csv", row=club_rows[cid], record_id=cid, field="club_id",
                       value=cid)
