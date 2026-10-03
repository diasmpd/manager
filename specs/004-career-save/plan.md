# Implementation Plan: Career Save and Game Loop

**Branch**: `004-career-save` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-career-save/spec.md`

## Summary

A `career` package turns the single-season engine into a career:
- **The career** holds a world, the current 002 season and its history. It is saved to one
  SQLite file per save, holding the world as 001's canonical CSV texts, the season definition
  and the played results with their 003 reports.
- **Loading** rebuilds the season deterministically and replays it with the stored results,
  so engine changes never rewrite a career's past.
- **The loop**: "Continuar" advances day by day and stops before the user's match days, at
  competition events and at the season end. It autosaves every in-game week.
- **Suspensions** follow real rules (a red card is one match; three yellows are one match).
  They are derived from match reports, and the quick sim leaves suspended players out of team
  sheets.
- **The rollover** at season end:
  - records the season's history;
  - replaces the relegated clubs with two generated promoted clubs;
  - ages players and applies a placeholder development curve;
  - lets players decide to retire;
  - refills squads with generated youngsters.

Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12

**Primary Dependencies**: standard library only (`sqlite3`, `json`, `tempfile`, `os`). No new
runtime dependency.

**Storage**: one SQLite file per save ([contracts/save-format.md](contracts/save-format.md)).
Saves are git-ignored. Development and retirement curves are TOML reference data.

**Testing**: pytest and hypothesis.
- Save/load round-trips at random stopping points (SC-001).
- Discipline invariants over 100 seasons.
- A 10-season rollover statistics test (`slow`).
- Atomic-write failure injection.

**Target Platform**: Windows 11, with Linux in CI.

**Project Type**: library + CLI (headless core)

**Performance Goals** (SC-002):
- a new career to season end in < 5 s, autosaves included;
- one continue between user matches in < 1 s.

**Constraints**:
- Deterministic: every rollover step is seeded from the career seed.
- Timestamps are for display only.
- pt-BR output.

**Scale/Scope**: 12 clubs and about 330 players per world. Saves are about 200 kB.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ / deferred | No new calibrated simulation. The development and retirement curves are explicit placeholders, with targets only for squad stability (SC-004) and retirement age (SC-005). Calibrated development is v1 and is stated in the spec. The quick sim calibration is unaffected: suspensions only change who plays. |
| II. Determinism | ✅ | Career seed → season seeds and rollover sub-seeds (SHA-256). Saves record the core and Python versions. Results are stored, so loading never re-simulates the past. |
| III. Headless core | ✅ | The `career` package plus facade. The CLI and the 005 TUI call only the facade. |
| IV. Test-first | ✅ | Round-trip, discipline and rollover tests are written before the code. Failure injection covers saves. |
| V. Smart automation | ✅ | Suspended players are left out automatically. The owner sees who and why. |
| VI. Data rights | ✅ | Generated clubs and players are fictional. Saves are local and git-ignored. |
| VII. Incremental | ✅ | No transfers, contracts, finances, Módulo II play or user relegation (owner: out of scope). The save format is versioned, with migrations, for v1. |
| Tech constraints | ✅ | SQLite per save, as the constitution requires. Standard library only. |
| Workflow | ✅ | Branch `004-career-save` and a PR. |

**Post-design re-check**: ✅ No violations.

## Project Structure

```text
core/src/manager_core/
├── career/
│   ├── __init__.py
│   ├── career.py        # Career, Stop, continue_ (loop, autosave), new_career
│   ├── discipline.py    # ledger derived from reports; suspended(club)
│   ├── rollover.py      # history, promotion, ageing, development, retirement, refill
│   ├── codec.py         # Result / MatchReport / history <-> JSON
│   ├── store.py         # SQLite save/load, atomic write, versions, migrations (V-codes)
│   └── recorded.py      # RecordedProvider: stored results first, quick sim after
├── reference/career/development.toml, retirement.toml, promoted-clubs.toml
├── sample/generator.py  # + make_player, make_club (refactor, same output)
├── competition/results.py, season.py   # MatchContext.unavailable, discipline hook
├── quicksim/provider.py # sheets per (club, unavailable)
├── api.py, cli.py       # career facade + `career` command group, `season --career`
└── i18n/pt_BR.py
core/tests/{unit,contract,integration}/…
.gitignore               # saves/
```

## Complexity Tracking

No constitution violations to justify.
