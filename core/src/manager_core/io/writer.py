"""Dataset -> folder, canonical and byte-stable (FR-021, contracts/csv-format.md v1.0)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from manager_core.domain.attributes import ALL_ATTRIBUTES
from manager_core.domain.dataset import Dataset, RecordType
from manager_core.domain.positions import MIN_FAMILIARITY, Position
from manager_core.io.dialect import format_value as f
from manager_core.io.dialect import write_table
from manager_core.io.schema import FILES


@dataclass(frozen=True, slots=True)
class ExportSummary:
    path: Path
    rows_per_file: dict[str, int]
    flags: dict[str, int]

    @property
    def clubs(self) -> int:
        return self.rows_per_file["clubs.csv"]

    @property
    def players(self) -> int:
        return self.rows_per_file["players.csv"]


def write(dataset: Dataset, path: Path) -> ExportSummary:
    path.mkdir(parents=True, exist_ok=True)
    d = dataset
    tables: dict[str, list[list[str]]] = {
        "dataset.csv": [[
            d.format_version, f(d.reference_date), f(d.fictional), d.tool, d.tool_version,
            f(d.seed), d.notes,
        ]],
        "sources.csv": [
            [s.name, f(s.url), f(s.retrieved_on), f(s.licence_notes)] for s in d.sources
        ],
        "clubs.csv": [
            [
                c.id, c.name, c.short_name, c.abbreviation, c.city, f(c.state), c.country,
                c.color_primary, c.color_secondary, c.stadium_name, f(c.stadium_capacity),
                f(c.founded_year), f(c.reputation),
            ]
            for c in d.clubs.values()
        ],
        "players.csv": [
            [
                p.id, p.full_name, p.display_name, f(p.date_of_birth), f(p.nationalities),
                f(p.height_cm), f(p.weight_kg), f(p.left_foot), f(p.right_foot),
                f(p.potential_ability),
            ]
            for p in d.players.values()
        ],
        "attributes.csv": [
            [p.id, *(f(p.attributes.get(n)) for n in ALL_ATTRIBUTES)] for p in d.players.values()
        ],
        "positions.csv": [
            [
                p.id,
                *(
                    "" if p.positions[pos] == MIN_FAMILIARITY else f(p.positions[pos])
                    for pos in Position
                ),
            ]
            for p in d.players.values()
        ],
        "squads.csv": [
            [
                m.player_id, m.club_id, f(m.shirt_number), f(m.market_value),
                f(m.wage_monthly), f(m.currency), f(m.contract_expiry),
            ]
            for m in d.memberships.values()
        ],
        "external_refs.csv": [
            [RecordType.CLUB.value, c.id, r.source, r.source_id]
            for c in d.clubs.values()
            for r in c.external_refs
        ]
        + [
            [RecordType.PLAYER.value, p.id, r.source, r.source_id]
            for p in d.players.values()
            for r in p.external_refs
        ],
        "record_flags.csv": [
            [fl.record_type.value, fl.record_id, fl.flag.value, fl.detail]
            for fl in d.record_flags
        ],
    }
    for name, rows in tables.items():
        spec = FILES[name]
        write_table(path / name, spec.names, rows)
    return ExportSummary(
        path=path,
        rows_per_file={name: len(rows) for name, rows in tables.items()},
        flags=dict(sorted(Counter(fl.flag.value for fl in d.record_flags).items())),
    )
