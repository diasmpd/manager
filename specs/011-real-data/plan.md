# Implementation Plan: Real Data for Minas Gerais Clubs

**Branch**: `011-real-data` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-real-data/spec.md`

## Summary

Build an import pipeline that turns public facts about the Campeonato Mineiro clubs into a game
dataset in the private `manager-data` repository. The pipeline has four stages:

1. **Collect**: fetch pages gently and cache them. Sources: ogol for squads and player facts
   (owner decision: private, paced, cached), Wikipedia for club identity and results.
2. **Parse and merge**: turn the cached pages into clubs and players with provenance, and report
   disagreements.
3. **Synthesise**: our own attribute-synthesis model gives every player an overall level and the
   full FM-style attributes, from league, club, minutes, age, position and value.
4. **Apply owner corrections**: field-level, they survive re-imports, and they are the audit trail.

The output is a dataset in the existing 001 format: it validates, loads and plays like the sample.
All code and model parameters are public. All data and caches are private.

## Technical Context

**Language/Version**: Python 3.12+ (core), as the rest of `manager_core`.

**Primary Dependencies**: standard library only (Constitution, as in 001–008):
- `urllib.request` for fetching;
- `html.parser` for parsing;
- `gzip` for the cache;
- `tomllib` for model parameters.

**Storage**:
- CSV dataset files (001 format v1, plus v1.1 tolerant reading) in `manager-data`;
- gzipped raw pages in `manager-data/cache/`;
- owner corrections in `manager-data/corrections.csv`.

**Testing**: pytest, with fictional HTML fixtures (no network, no private data in tests). The
synthesis model is tested on the fictional sample.

**Target Platform**: Windows, as the rest of the game.

**Project Type**: core library plus CLI tooling (`python -m manager_core.realdata`).

**Performance Goals**:
- a full Módulo I re-import from cache in at most 10 minutes (SC-005);
- a first collection limited by pacing alone: about 12 club pages and about 350 player pages at
  4 s or more each, under 30 minutes, run once and then cached.

**Constraints**:
- no real data in the public repository, enforced by a test that scans tracked files (SC-006);
- deterministic output from the same cache and corrections (FR-006);
- robots.txt obeyed, an honest user agent, at least 4 s between requests to one host.

**Scale/Scope**:
- Módulo I: 12 clubs and about 350 players;
- Módulo II (P3): 12 clubs and about 300 players.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan meets it |
|---|---|
| I. Realism is measured | Synthesis checked against real outcomes (SC-003 rank correlation 0.7 or more against the 2026 Mineiro), plus the owner's plausibility check of a quick-sim season (SC-008). Game calibration targets unchanged. |
| II. Deterministic | Same cache plus same corrections gives an identical dataset. Model "noise" is seeded by player id. |
| III. Headless core, thin client | All in `manager_core`. The client only reads the dataset (club colours already flow through contract 1.3). |
| IV. Test-first | Parsers tested on fictional HTML fixtures. Model tested on the sample. Corrections and Excel round trips tested. |
| V. Manager in control | The owner review step: corrections always win and survive re-imports. |
| VI. Data rights | Data and caches only in private `manager-data`. Provenance per record (`sources.csv`, `external_refs.csv`). A guard test forbids real data in the public repo. No other game's ratings are inputs. |
| VII. Incremental | US1 survey, then Módulo I, then the model, then review, then Módulo II and Excel. Extension points: more sources and states later. |

**Result**: pass. No violations. Re-checked after Phase 1 (data model and CLI): still pass.

## Project Structure

### Documentation (this feature)

```text
specs/011-real-data/
├── plan.md              # This file
├── research.md          # R1 source survey; R2–R7 design decisions
├── data-model.md        # Entities and the private repository's layout
├── quickstart.md        # Validation scenarios
├── contracts/
│   └── realdata-cli.md  # The import CLI
└── tasks.md             # /speckit-tasks
```

### Source Code (public repository)

```text
core/src/manager_core/realdata/
├── __init__.py
├── __main__.py          # CLI: collect | build | report | check-public
├── fetch.py             # paced, cached, robots-aware fetcher (honest user agent)
├── sources/
│   ├── ogol.py          # club squad page and player page parsers
│   └── wikipedia.py     # club infobox and competition-table parsers
├── merge.py             # identities, precedence, disagreements, provenance
├── synthesis.py         # the attribute-synthesis model
├── corrections.py       # owner corrections: apply, audit, carry across imports
└── build.py             # pipeline: cache to dataset (001 writer), plus the report
core/src/manager_core/reference/synthesis/
├── model.toml           # model parameters (data, public)
└── profiles.toml        # position profiles and age curves
core/src/manager_core/io/dialect.py   # + pt-BR Excel tolerance (format v1.1)
core/tests/
├── fixtures/realdata/   # fictional ogol and Wikipedia HTML pages
├── unit/test_realdata_*.py
└── integration/test_realdata_build.py, test_no_real_data.py
```

### Private repository (`manager-data`)

```text
manager-data/
├── inputs/mineiro.toml        # club list: ids per source, owner-given colours
├── cache/ogol/…, cache/wikipedia/…   # gzipped raw pages plus fetch log
├── corrections.csv            # owner corrections (the field-level audit trail)
└── datasets/mineiro-2026/     # the built dataset (001 format) plus import-report.md
```

**Structure Decision**: the pipeline is a `manager_core` subpackage. It is typed and tested with
the core, and it reuses the 001 reader, writer and validator. The private repository holds only
inputs, caches, corrections and outputs.

## Complexity Tracking

No constitution violations to justify.
