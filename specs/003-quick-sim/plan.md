# Implementation Plan: Quick Sim

**Branch**: `003-quick-sim` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-quick-sim/spec.md`

## Summary

A minute-by-minute statistical match simulator replaces 002's placeholder results:
- **Team ratings.** Six composites (attack, control, defence, goalkeeping, set pieces and
  discipline) are computed from the FM attributes of the players on the pitch.
- **Events.** Each minute, they drive shots with xG, goals, fouls, cards, corners and
  penalties. Home advantage, a time trend and game-state behaviour (chasing, protecting a lead,
  red cards, booked-player caution) shape the match.
- **Players.** Players score, assist, get booked and are substituted, and shootouts use the
  takers and the keeper.
- **Parameters.** They are data (`model.toml`), fitted by a dev tuning tool against real-data
  targets stored with their sources.
- **Calibration.** A deterministic harness gives the PR and milestone gates, with before/after
  reports.

Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12 (as 001/002)

**Primary Dependencies**: standard library only (`random`, `math`, `tomllib`, `hashlib`,
`json`). No new runtime dependency.

**Storage**: model parameters and calibration targets as TOML reference data. The calibration
baseline is a committed JSON file (`core/calibration/`). Match reports live in memory on
`Result`. Persistence is spec 004.

**Testing**: pytest and hypothesis.
- Per-match invariants over thousands of matches.
- Statistical behaviour tests with fixed seeds and tolerance bands (Constitution IV).
- The calibration gate as a test (PR sample) plus a `slow` milestone test.

**Target Platform**: Windows 11 (reference PC), with Linux in CI.

**Project Type**: library + CLI (headless core)

**Performance Goals** (SC-004):
- a Mineiro matchday in < 0.5 s;
- a full Mineiro season in < 3 s;
- a 10-match league matchday in < 1 s;
- the PR calibration gate in < 30 s.

**Constraints**:
- Deterministic per match seed.
- Parameters are data, with a hash in every report.
- pt-BR output through i18n.
- No tactics (spec 006).

**Scale/Scope**: M0 has 12 clubs. The design must scale to v1's world (about 300 matches per
in-game weekend). That works at about 2 ms per match once lineups are cached.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | Targets carry named sources and retrieval dates (spec table, R14), stored as data. The harness has two tiers: PR (about 5,600 matches) and milestone (about 43,000). Before/after reports are required in the PR. The **exploit check** is deferred to spec 006, because there are no tactics to exploit yet. The deviation is stated in spec FR-020, and FM's approach is noted in the spec header. |
| II. Determinism | ✅ | One RNG per match from 002's `sub_seed`. Sorted iteration over players. Reports record the core, Python and model versions plus the parameter hash. Canonical JSON. |
| III. Headless core | ✅ | The sim lives in `quicksim/`. The CLI reads views through the facade only. |
| IV. Test-first | ✅ | Invariant, behaviour and statistical tests are written before the model. The calibration gate runs in the suite. |
| V. Smart automation | ✅ | Booked-player caution with a measured trade-off (SC-006), on by default and logged in the report. Automatic substitutions in the quick sim are background behaviour, not the user's match (the assistant is spec 009). |
| VI. Data rights | ✅ | Only aggregate league statistics are committed (allowed by Principle I). There are no real players. |
| VII. Incremental | ✅ | No tactics, fatigue across matches, injuries or suspensions. Cards are recorded per player so those can come later. |
| Tech constraints | ✅ | Standard library only. The two-tier engine is honoured: the quick sim is calibrated independently of 007, and cross-validation is deferred until 007 exists. |
| Workflow | ✅ | Branch `003-quick-sim` on top of 002 (PR #2), and the PR includes the fast-gate report. |

**Post-design re-check**: ✅ No violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-quick-sim/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── facade.md
│   ├── cli.md
│   └── calibration-targets.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
core/src/manager_core/
├── quicksim/
│   ├── __init__.py
│   ├── params.py         # ModelParams + loader/validator (Q-codes), params_hash
│   ├── ratings.py        # TeamRatings composites from players on the pitch
│   ├── squad.py          # MatchSquad: XI + bench (cached per club), substitutions
│   ├── report.py         # Minute, MatchEvent, SideStats, MatchReport (+ invariants check)
│   ├── engine.py         # simulate_match(): minute loop, game state, events
│   ├── shootout.py       # player-based shootout
│   └── provider.py       # QuickSimProvider (ResultProvider)
├── calibration/
│   ├── __init__.py
│   ├── targets.py        # targets file loader (C-codes)
│   ├── samples.py        # league + Mineiro samples, fixed seeds
│   ├── metrics.py        # metric functions by id
│   └── harness.py        # run, compare to baseline, canonical JSON report
├── reference/
│   ├── quicksim/model.toml
│   └── calibration/quicksim-targets.toml
├── competition/results.py, season.py   # Result.report, MatchContext.neutral, shootout last_result
├── api.py                # match_report, season_scorers, run_calibration; default provider
├── cli.py                # season match, season scorers, calibrate
└── i18n/pt_BR.py         # stat labels, event texts, calibration report
core/tools/tune_quicksim.py   # dev-only parameter fitting (not shipped in the package)
core/calibration/quicksim-baseline.json
core/tests/
├── unit/        # params, ratings, squad/subs, report invariants, engine behaviour, shootout
├── contract/    # targets file, CLI match/scorers/calibrate, facade
└── integration/ # seasons with quick sim, calibration gate (PR + slow milestone), performance
```

**Structure Decision**:
- **Dependencies.** A new `quicksim` package depends on `domain`, `ratings` and
  `competition.results`. `calibration` depends on `quicksim` and `competition`.
- **Imports into 002's code.** The 002 season engine imports nothing from `quicksim`. Only
  `api.start_season` picks the default provider, so the competition package stays independent
  of the engine tier.

## Complexity Tracking

No constitution violations to justify.
