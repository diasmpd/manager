# Implementation Plan: Competitions and Calendar

**Branch**: `002-competitions-calendar` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-competitions-calendar/spec.md`

## Summary

This feature adds a data-driven competition engine:
- rulesets in TOML, with the FMF Mineiro 2026 format first and a structurally different test
  format to prove the rules really are data;
- a seeded FMF-style group draw;
- cross-group fixture generation by exact perfect matching;
- a date scheduler (weekends first, midweek rounds to fit the window, a 66-hour minimum rest,
  reserved windows avoided);
- tables with an auditable tiebreaker trail;
- knockout tracks (two-leg semifinals with penalties, a neutral single final, and the Troféu
  Inconfidência as a side track);
- relegation outcomes;
- a full-year calendar.

The season advances day by day in memory. Results come from a labelled placeholder provider
behind a `ResultProvider` interface that spec 003 replaces. The CLI rebuilds and replays the
season deterministically per command. Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12 (as 001)

**Primary Dependencies**: standard library only (`tomllib`, `hashlib`, `datetime`, `random`). No
new runtime dependency.

**Storage**: rulesets and calendar windows as TOML reference data in the package. Season state in
memory (saves are spec 004).

**Testing**: pytest and hypothesis.
- Invariants over 200 seeded seasons in the regular suite, 1,000 under `slow`.
- Hand-built tiebreak scenarios.
- One broken ruleset per R-code.

**Target Platform**: Windows 11, with Linux in CI

**Project Type**: library + CLI (headless core)

**Performance Goals**: start and play a full season in under 2 s (SC-005).

**Constraints**:
- Deterministic: sub-seeds from SHA-256, never `hash()`.
- pt-BR output.
- The placeholder provider must be clearly labelled and replaceable.

**Scale/Scope**: M0 has one competition of 12 clubs. The design must allow about 30 competitions
per season in v1 without new stage types for common Estadual formats.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | No calibrated simulation here. The placeholder is explicitly not a realism target (spec Assumptions), and realism is spec 003's job. The Mineiro format follows named press sources (spec header), and unconfirmed rules are listed for checking against the FMF regulation. |
| II. Determinism | ✅ | Season seed and per-decision sub-seeds via SHA-256 (R4). Sorted iteration, stable match ids, replay-equal tests. The CLI replays seasons instead of keeping state. |
| III. Headless core, thin client | ✅ | All rules live in `competition/`. The CLI calls only the facade. Results go through a provider interface. |
| IV. Test-first | ✅ | Invariant, statistical and scenario tests are written before the engine, with fixtures per R-code. |
| V. Smart automation | ✅ (n/a) | No player behaviour here. |
| VI. Data rights | ✅ | Fictional neutral venue. Real rulesets and venue names can live in `manager-data`. |
| VII. Incremental | ✅ | Only two stage types (groups, knockout). Reserved windows are labels only. No Copa do Brasil or Série D places (owner). |
| Tech constraints | ✅ | Standard library only. pt-BR via i18n. Performance budget stated. |
| Workflow | ✅ | Feature branch and PR, with CI from 001. |

**Post-design re-check**: ✅ No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-competitions-calendar/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── ruleset-format.md
│   ├── cli.md
│   └── facade.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
core/src/manager_core/
├── competition/
│   ├── __init__.py
│   ├── rules.py          # Ruleset dataclasses + TOML loader/validator (R-codes)
│   ├── seeds.py          # season seed + sub-seeds (SHA-256)
│   ├── draw.py           # pots_by_reputation / fixed
│   ├── fixtures.py       # own_group / other_groups / all matchings, home-away balance
│   ├── scheduler.py      # slots, rounds, dates, kick-offs, rest validation
│   ├── standings.py      # tables, tiebreakers with decided-by trail, overall classification
│   ├── knockout.py       # entrants, pairing, ties, legs, shootouts, tie rules
│   ├── results.py        # Result, Shootout, ResultProvider protocol, PlaceholderProvider
│   ├── season.py         # Season engine: start, advance_to, transitions, outcomes, views
│   └── calendar.py       # SeasonCalendar, reserved windows
├── reference/
│   ├── competitions/
│   │   ├── mg-modulo-i-2026.toml
│   │   └── test-liga-unica.toml
│   └── calendar/brazil.toml
├── api.py                # + season facade functions
├── cli.py                # + `season` command group
└── i18n/pt_BR.py         # + competition strings
core/tests/
├── unit/        # seeds, draw, fixtures, scheduler, standings, knockout, placeholder
├── contract/    # ruleset format, facade, CLI season commands
├── integration/ # full seasons (invariants, determinism, outcomes, test ruleset, performance)
└── fixtures/rulesets/   # one broken TOML per R-code + tiebreak scenarios
```

**Structure Decision**: a new `competition` package inside the existing core. It depends on
`domain` (clubs, reputation) and `ratings` (CA for team strength), and nothing depends on it yet.

## Complexity Tracking

No constitution violations to justify.
