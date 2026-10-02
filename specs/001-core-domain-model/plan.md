# Implementation Plan: Core Domain Model

**Branch**: `001-core-domain-model` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-core-domain-model/spec.md`

## Summary

This feature builds the immutable domain model that every later spec depends on:
- clubs and players with Football Manager's full attribute set (60 attributes, including hidden
  ones), stored Potential Ability and derived Current Ability;
- FM position familiarity, data-driven position suitability and an exact best-XI assignment;
- a basic formation catalogue.

Data moves through a versioned, Excel-friendly CSV format (pt-BR Excel dialect tolerated) with
mandatory provenance, all-or-nothing validation that reports every issue, lossless export and
manual-edit detection. A deterministic generator produces a committed, fictional
Mineiro-sized sample world. Everything is reached through a thin facade, with a pt-BR CLI on
top. Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12 (CI on 3.12 and 3.14)

**Primary Dependencies**: standard library only at runtime. Dev: pytest, hypothesis, ruff, mypy.

**Storage**: CSV dataset folders (`data/sample/`, `manager-data`). There is no database in 001
(SQLite saves are spec 004).

**Testing**: pytest (unit, contract, integration), hypothesis property tests, one invalid
fixture per error code.

**Target Platform**: Windows 11 (primary), with Linux in CI

**Project Type**: library + CLI (headless core)

**Performance Goals**: load and validate the sample world (about 324 players) in under 2 s, and
compute a best XI in under 0.5 s.

**Constraints**:
- Deterministic: sorted iteration, no set-order dependence, byte-stable export.
- pt-BR user-facing text through i18n.
- Tolerant of files saved by pt-BR Excel.

**Scale/Scope**: M0 datasets have about 12 clubs and 350 players. The design must stay
practical for a v1 world of about 50k players (no quadratic validation).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | No simulation in 001. Realism proxies are measurable: SC-005 (attribute coherence) and CA bands calibrated to FM ranges (R8). FM is the benchmark for attributes, bands and key attributes. No calibration harness is needed yet. |
| II. Determinism | ✅ | Generator owns its RNG (R14). Sorted iteration, canonical byte-stable export (R4), deterministic tie-breaking in best XI (R9). Dataset records tool version and seed. Core/Python version recording applies to saves and calibration reports (specs 003/004), not to datasets. |
| III. Headless core, thin client | ✅ | Facade `manager_core.api` (contracts/facade.md). The CLI calls only the facade and holds no rules. |
| IV. Test-first | ✅ | Tests precede implementation per task. Property tests for monotonicity and round-trip. One fixture per E-code. |
| V. Smart automation | ✅ (n/a) | No match behaviour in 001. Hidden attributes (temperament etc.) are modelled so 007 can drive behaviour from them. |
| VI. Data rights | ✅ | The sample world is fictional (FR-024). The format requires provenance (E032). No real data is in the repo. `/data/real/` is git-ignored. |
| VII. Incremental | ✅ | Milestone 0. Contracts, transfers, development and roles are excluded. The formation catalogue is data-driven, leaving room for the owner's custom-formation direction without building it. |
| Tech constraints | ✅ | Python ≥ 3.12. Stdlib runtime (no new runtime dependencies to justify). PT-BR via i18n. SQLite is not needed until 004. |
| Workflow | ✅ | Feature branch and PR. CI is introduced here (first code spec). |

**Post-design re-check**: ✅ No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-domain-model/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── csv-format.md
│   ├── cli.md
│   └── facade.md
├── checklists/requirements.md
└── tasks.md            # created by /speckit-tasks
```

### Source Code (repository root)

```text
core/
├── pyproject.toml
├── src/manager_core/
│   ├── __init__.py          # version
│   ├── __main__.py          # python -m manager_core → cli.main
│   ├── api.py               # facade (contracts/facade.md)
│   ├── cli.py               # argparse CLI, calls api only
│   ├── i18n/
│   │   ├── __init__.py      # t(key, **params)
│   │   └── pt_BR.py         # message catalogue
│   ├── domain/
│   │   ├── attributes.py    # Attributes, ATTRIBUTE_GROUPS, hidden defaults
│   │   ├── positions.py     # Position, lines, familiarity bands/factor
│   │   ├── club.py
│   │   ├── player.py
│   │   ├── squad.py         # SquadMembership
│   │   ├── formation.py     # Formation, FormationSlot, catalogue loader
│   │   └── dataset.py       # Dataset (World), queries, provenance types
│   ├── ratings/
│   │   ├── suitability.py   # base + familiarity factor (R7)
│   │   ├── ability.py       # derived CA (R8)
│   │   └── lineup.py        # bitmask-DP best XI (R9)
│   ├── io/
│   │   ├── dialect.py       # Excel-tolerant read, canonical write (R4)
│   │   ├── schema.py        # column specs per file (single source with ATTRIBUTE_GROUPS)
│   │   ├── validate.py      # raw-row validation → ValidationReport
│   │   ├── reader.py        # folder → Dataset (all-or-nothing)
│   │   ├── writer.py        # Dataset → folder (+ integrity.csv)
│   │   └── integrity.py     # canonical hashing, edit detection (R6)
│   ├── sample/
│   │   ├── generator.py     # deterministic world generator (R14)
│   │   └── names.py         # fictional clubs/towns/first/last names
│   └── reference/           # bundled CSV reference data
│       ├── formations.csv
│       ├── nations.csv
│       └── position_weights.csv
└── tests/
    ├── unit/                # attributes, positions, suitability, ability, lineup, dialect
    ├── contract/            # CSV format v1.0, facade signatures, CLI exit codes
    ├── integration/         # sample load/validate/export round-trip, determinism, Excel-dialect fixture
    └── fixtures/
        ├── valid/minimal/   # 2 clubs, hand-built
        ├── invalid/E0xx_*/  # one folder per error code
        └── excel_ptbr/      # ; + BOM + CRLF + DD/MM/YYYY + 15.000.000
data/
└── sample/                  # committed fictional world (generated)
.github/workflows/ci.yml
```

**Structure Decision**: a single Python project in `core/` (src layout), leaving `client/`
free for the Godot app (spec 010). The committed sample world lives in `data/sample/` next to
the git-ignored `data/real/`. `.gitattributes` adds `*.csv text eol=lf` so the committed files
are byte-stable.

## Complexity Tracking

No constitution violations to justify.
