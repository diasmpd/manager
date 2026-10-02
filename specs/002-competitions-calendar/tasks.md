---
description: "Task list for 002 Competitions and Calendar"
---

# Tasks: Competitions and Calendar

**Input**: Design documents from `specs/002-competitions-calendar/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED (Constitution IV). Write the tests first and see them fail.

**Paths**: the package is `core/src/manager_core/`; tests are in `core/tests/`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create the package `core/src/manager_core/competition/__init__.py` and the reference folders `core/src/manager_core/reference/competitions/` and `core/src/manager_core/reference/calendar/`, each with `__init__.py` so `importlib.resources` can read them. Add `reference/competitions/*.toml` and `reference/calendar/*.toml` to package data in `core/pyproject.toml`.
- [X] T002 [P] Create the test folders `core/tests/fixtures/rulesets/` and `core/tests/fixtures/tiebreaks/`

---

## Phase 2: Foundational (blocks all stories)

### Tests first

- [X] T003 [P] Unit tests `core/tests/unit/test_seeds.py`:
  - `season_seed(master, year)` is stable across runs and differs by year and master;
  - `sub_seed(seed, label)` is stable and label-sensitive;
  - Python `hash()` is never used (assert values for known inputs).
- [X] T004 [P] Contract test `core/tests/contract/test_ruleset_format.py`:
  - `mg-modulo-i-2026.toml` loads into the `Ruleset` dataclasses with exactly the values in contracts/ruleset-format.md: 12 participants, `regulation_year` 2026 and `valid_from` 2026, 3×4 groups, `other_groups`, 1 round, tiebreaker order, window 01-08 to 03-08, 66 h, neutral venue "Arena Estadual das Gerais", Inconfidência entrants `overall_places [5, 8]` with `exclude_tracks = ["main"]`, Inconfidência final `may_exceed_window = true`;
  - five stages in order, with the tracks `main` and `inconfidencia` and their titles.
- [X] T005 [P] Unit tests `core/tests/unit/test_results.py`: `Result` and `Shootout` invariants (non-negative goals, the shootout winner consistent with the kicks, sudden death after 5 each), `source` is required, and `PlaceholderProvider` satisfies the `ResultProvider` protocol.

### Implementation

- [X] T006 [P] Implement `core/src/manager_core/competition/seeds.py`: `season_seed(master_seed: int, year: int) -> int` and `sub_seed(seed: int, label: str) -> int`, both via SHA-256 (research R4).
- [X] T007 [P] Implement `core/src/manager_core/competition/rules.py`:
  - frozen dataclasses `Ruleset`, `Scoring`, `CalendarRule`, `NeutralVenue`, `GroupStageRule`, `KnockoutStageRule`, `EntrantRule`, `OutcomeRule`;
  - enums `Tiebreaker`, `Matching`, `Pairing`, `TieRule`, `Venue`;
  - `load_ruleset(id)` (bundled) and `load_ruleset_file(path)`, using `tomllib`;
  - a `RulesetReport` with codes R001–R014 from data-model.md, collecting every problem before any object is built;
  - `list_rulesets()`.
- [X] T008 [P] Write `core/src/manager_core/reference/competitions/mg-modulo-i-2026.toml` exactly per contracts/ruleset-format.md, with comments citing the press sources from the spec header and marking the unconfirmed rules ("a confirmar no regulamento FMF 2026").
- [X] T009 [P] Write `core/src/manager_core/reference/calendar/brazil.toml` with fixed windows and the Easter-based Carnival windows from contracts/ruleset-format.md (Carnival Saturday to Ash Wednesday labelled; Monday and Tuesday `blocks = ["state"]`), plus `brazil-2027.toml` with the 2027 FIFA windows (dates marked approximate). Fixed reserved windows (month-day, labels, blocks):
  - FIFA windows 03-23–03-31, 06-01–06-09, 09-01–09-09, 10-05–10-13 and 11-09–11-17, each `blocks = ["state"]`;
  - "Copa do Brasil (fases iniciais)" 02-18–05-31;
  - "Brasileirão Séries A–D" 03-28–12-06;
  - all marked approximate in comments.
- [X] T010 Implement `core/src/manager_core/competition/results.py`:
  - `Result` (home/away goals, `source`, optional cards, optional `Shootout`) and `Shootout` (kicks, winner);
  - the `ResultProvider` protocol and `MatchContext`;
  - `PlaceholderProvider`, per research R9:
    - strength = mean CA of the top 11 players with at least 1 GK;
    - goals are Poisson with λ_home = 1.30·e^{0.020·ΔS} and λ_away = 1.05·e^{−0.020·ΔS};
    - penalties score with p = 0.75, then sudden death;
    - the RNG is seeded from `sub_seed(season_seed, "match:{id}")`;
    - `source = "placeholder"`;
    - strengths are cached per club.
- [X] T011 Add competition strings to `core/src/manager_core/i18n/pt_BR.py`:
  - R-code messages, stage and track names, zone labels (Semifinal / Troféu Inconfidência / Rebaixado);
  - table column labels, weekday and month names;
  - "(provisório)", event texts (sorteio, classificado, rebaixado, campeão);
  - tiebreaker names.
- [X] T012 Add the facade signatures from contracts/facade.md to `core/src/manager_core/api.py` (they raise `NotImplementedError` until implemented), and add a `season` command group skeleton to `core/src/manager_core/cli.py`. The skeleton has the shared options `--ruleset`, `--year`, `--master-seed` and `--date`, a helper that rebuilds the season and replays it to the date, and exit codes 0/1/2/3.

**Checkpoint**: seeds, rulesets, results and the skeletons pass their tests.

---

## Phase 3: User Story 1 - Start a Mineiro season (P1) 🎯 MVP

**Goal**: groups drawn, fixtures built and dates assigned for the Mineiro first phase.

**Independent Test**:
- `season groups` and `season fixtures` on the sample world.
- The invariants hold on 200 seeds.
- A replay is identical.

### Tests (first)

- [X] T013 [P] [US1] Unit tests `core/tests/unit/test_draw.py`:
  - `pots_by_reputation`: pot 1 = the 3 highest reputations (ties broken by id), one per group;
  - every pot is dealt one club per group;
  - the result is deterministic per seed, and different seeds give different draws in at least 1 of 20;
  - `fixed` reads groups from the ruleset.
- [X] T014 [P] [US1] Unit tests `core/tests/unit/test_fixtures.py` for `other_groups` on 200 seeds:
  - each club plays 8 matches, against exactly the 8 clubs of the other groups, never its own group;
  - every club appears exactly once per matchday (8 matchdays × 6 matches);
  - home/away is 4–4 for every club.

  Also: `all` with double round is a double round-robin, with `n−1` rounds per leg, each pair meeting once home and once away; `own_group` is a round-robin inside each group.
- [X] T015 [P] [US1] Unit tests `core/tests/unit/test_scheduler.py` on 200 seeds:
  - all first-phase dates are inside the window, and the window starts on the first weekend on or after 01-08;
  - weekend slots are used before any midweek slot;
  - no date falls in a window with `blocks = ["state"]`;
  - no club has two matches less than 66 h apart (kick-off to kick-off);
  - kick-offs are 16:00 on weekends and 21:30 midweek;
  - a window too short for the rounds raises a clear `SchedulingError`;
  - **rest boundary** (review item 5): Wednesday 21:30 → Saturday 16:00 is accepted (66.5 h), and the same with a 22:00 kick-off is rejected; a Thursday club is never placed on Saturday;
  - **Carnival**: Easter dates are correct for 2026–2030 (known values), and no state match falls on Carnival Monday or Tuesday for any year 2026–2030 on 200 seeds;
  - **window**: every round stays inside the window except stages with `may_exceed_window` (only the Inconfidência final legs), on 200 seeds × years 2026–2030.
- [X] T016 [P] [US1] Integration test `core/tests/integration/test_season_start.py`:
  - `start_season(sample, "mg-modulo-i-2026", 2027, 20261002)` gives 3 groups headed by `vale-do-ouro`, `serra-negra` and `alvorada`;
  - 48 first-phase matches with stable ids and venues equal to the home club's stadium;
  - two starts are field-by-field equal (SC-002 for the start);
  - starting with the wrong number of participants is refused with a clear message (S002);
  - starting in a year before `valid_from` (e.g. 2025) is refused (S001).
- [X] T017 [P] [US1] Contract test `core/tests/contract/test_cli_season_start.py`: `season groups` and `season fixtures [--round N | --club ID]` exit 0 and print the documented columns; an unknown club exits 3.

### Implementation

- [X] T018 [P] [US1] Implement `core/src/manager_core/competition/draw.py`: `draw_groups(clubs, rule, seed) -> list[Group]` with `pots_by_reputation` and `fixed` (research R5).
- [X] T019 [P] [US1] Implement `core/src/manager_core/competition/fixtures.py`:
  - `build_group_stage_fixtures(groups, matching, rounds, seed)` → matchdays of pairings;
  - `other_groups` uses an exact perfect-matching search per matchday (research R6);
  - `all` and `own_group` use the circle method;
  - a home/away balancing pass gives 4–4 for `other_groups` and alternation for round-robins.
- [X] T020 [US1] Implement `core/src/manager_core/competition/scheduler.py`:
  - window resolution for a year;
  - slot generation (weekends, midweeks) minus blocked windows;
  - main-path slot selection (all weekends, then evenly spread midweeks);
  - day/kick-off assignment inside a slot so that a club that played midweek gets the later weekend day;
  - `validate_rest(matches, min_hours)`;
  - `SchedulingError` (research R7).
- [X] T021 [US1] Implement the start of the `Season` engine in `core/src/manager_core/competition/season.py`:
  - `Season.start(dataset, ruleset, year, master_seed, participants, provider)`: validates the participants, draws, builds the fixtures, schedules the group stage, creates `Match` objects with stable ids and venues, and logs the `draw` event;
  - the views `groups()` and `fixtures(club_id, round)`.
- [X] T022 [US1] Facade: implement `start_season`, `season_groups` and `season_fixtures` in `core/src/manager_core/api.py`.
- [X] T023 [US1] CLI: implement `season groups` and `season fixtures` in `core/src/manager_core/cli.py`, with dates in pt-BR (e.g. "dom 10/01/2027 16:00").

**Checkpoint**: a season can be started and inspected. MVP.

---

## Phase 4: User Story 2 - Play the season day by day (P2)

**Goal**: results, tables with tiebreakers, qualification, knockouts with shootouts, the side track, relegation and outcomes.

**Independent Test**: play 200 seasons to the end and check SC-001; tiebreak scenarios; CLI views.

### Tests (first)

- [ ] T024 [P] [US2] Create at least 10 hand-built tiebreak scenarios in `core/tests/fixtures/tiebreaks/*.toml`, each with clubs, match results with optional cards, and the expected order. Cover:
  - a two-way tie settled by wins, by goal difference and by goals scored;
  - head-to-head between two clubs that met;
  - head-to-head skipped (clubs never met);
  - a three-way tie (head-to-head not applied);
  - a card tiebreak;
  - a cards-missing tie that falls through to lots;
  - a full tie settled by seeded lots;
  - best second-placed club compared across groups.
- [ ] T025 [P] [US2] Unit tests `core/tests/unit/test_standings.py`:
  - parametrised over the tiebreak scenarios (SC-004): order and the `decided_by` trail;
  - points 3/1/0;
  - the table columns are consistent (P = W + D + L, GD = GF − GA);
  - the overall classification across groups.
- [ ] T026 [P] [US2] Unit tests `core/tests/unit/test_knockout.py`:
  - entrants: group winners + best 2nd; overall places 5–8 with `exclude_tracks`: a semifinalist placed 5th–8th is skipped and the next eligible place fills in (hand-built table where 2 semifinalists rank 6th and 7th → entrants are 5th, 8th, 9th, 10th);
  - pairing `campaign_1v4_2v3`;
  - the better campaign hosts the second leg;
  - an aggregate tie goes to penalties (no away goals);
  - `points_then_campaign` resolves a level tie by points over the legs, then campaign, with no shootout;
  - the single final is at the neutral venue;
  - a shootout runs 5 kicks each plus sudden death, and its winner matches the kicks.
- [ ] T027 [P] [US2] Unit tests `core/tests/unit/test_placeholder.py`:
  - results are deterministic per match id regardless of play order;
  - over 2,000 simulated matches the scorelines are plausible: mean goals in 2.0–3.0, home wins > away wins, and a stronger side wins more (sanity only, not calibration);
  - `source == "placeholder"`.
- [ ] T028 [P] [US2] Integration test `core/tests/integration/test_season_play.py`:
  - 200 seeds played to the end; the 1,000-seed version is marked `slow` (SC-001);
  - exactly 1 champion, 2 finalists, 4 semifinalists, 4 Inconfidência entrants and 2 relegated clubs, consistent with the final tables;
  - the relegated clubs are 11th and 12th overall;
  - no club is ever in both tracks (regression for the review's 55% overlap finding), and the Inconfidência entrants are the first four non-semifinalists from place 5 onward;
  - only the Inconfidência final may fall after the window end;
  - knockout dates come after the first phase;
  - no rest violations across all matches, including knockouts;
  - outcomes are identical on replay (SC-002).
- [ ] T029 [P] [US2] Integration test `core/tests/integration/test_season_advance.py`:
  - `advance_to` on a day with no matches only moves the date;
  - advancing in daily steps equals advancing in one jump;
  - advancing past 31 December is refused;
  - events are emitted in date order (draw, qualified, paired, relegated, champion, side champion).
- [ ] T030 [P] [US2] Contract test `core/tests/contract/test_cli_season_play.py`:
  - `season table [--group A | --overall] [--date]`, `season bracket`, `season day --date` and `season outcomes` exit 0 with the documented columns;
  - placeholder results are marked "(provisório)";
  - an unknown group exits 3.
- [ ] T031 [P] [US2] Performance test `core/tests/integration/test_season_performance.py` (`slow`, limit from `MANAGER_PERF_LIMIT_S`): starting and playing a full season takes < 2 s (SC-005).

### Implementation

- [ ] T032 [US2] Implement `core/src/manager_core/competition/standings.py`:
  - `build_table(club_ids, matches, scoring, tiebreakers, seed, label)`;
  - recursive per-criterion splitting with the `decided_by` trail (research R8);
  - head-to-head only for exactly two clubs that met;
  - card criteria neutral when cards are missing;
  - seeded lots via `sub_seed`;
  - `overall_classification` across groups.
- [ ] T033 [US2] Implement `core/src/manager_core/competition/knockout.py`:
  - entrant resolution (`group_winners`, `best_of_place`, `overall_places`, `winners_of`);
  - pairing and leg hosting;
  - `KnockoutTie` resolution for `penalties` and `points_then_campaign`;
  - neutral venue for `venue = "neutral"`.
- [ ] T034 [US2] Extend `Season` in `core/src/manager_core/competition/season.py`:
  - `advance_to(date)` plays each day's matches in kick-off order through the provider and updates the tables;
  - when a stage completes, it decides qualification, records relegation outcomes and pairs the next knockout rounds (main and side tracks);
  - it schedules the new rounds through the scheduler, using the `dates_with` slots for side tracks;
  - it detects track completion and records the `Outcome`;
  - the views `table(group)`, `bracket()`, `day(date)` and `outcomes()`.
- [ ] T035 [US2] Facade: implement `advance_to`, `season_table`, `season_bracket`, `season_day` and `season_outcomes` in `core/src/manager_core/api.py`.
- [ ] T036 [US2] CLI: implement `season table`, `season bracket`, `season day` and `season outcomes` in `core/src/manager_core/cli.py`, with zone markers, the decided-by note, aggregates and shootouts, "(provisório)" on placeholder results, and pt-BR dates.

**Checkpoint**: a full Mineiro season plays out with correct outcomes.

---

## Phase 5: User Story 3 - Each state has its own rules (P3)

**Goal**: prove that rulesets are data. A second format plays without code changes, and broken files are rejected.

**Independent Test**: play `test-liga-unica` to the end; every R-code fixture is rejected with its code.

### Tests (first)

- [ ] T037 [P] [US3] Write `core/src/manager_core/reference/competitions/test-liga-unica.toml`, a structurally different format:
  - 8 clubs, `matching = "all"`, 2 rounds (double round-robin);
  - tiebreakers `["goal_difference", "wins", "goals_for", "draw"]`;
  - a two-leg final between 1st and 2nd with `tie_rule = "points_then_campaign"`;
  - places 8 relegated;
  - no neutral venue;
  - window 01-15 to 04-30.
- [ ] T038 [P] [US3] Create one broken ruleset per R-code in `core/tests/fixtures/rulesets/R0xx_*.toml` (R001–R014), each with an `expected.txt`. R012 = a side track on `overall_places` overlapping the main track's entrants without `exclude_tracks`.
- [ ] T039 [P] [US3] Contract test `core/tests/contract/test_ruleset_validation.py`: every R-fixture is rejected with its code and location (key path), a file with 3 defects reports all 3, and both bundled rulesets validate clean (SC-006).
- [ ] T040 [P] [US3] Integration test `core/tests/integration/test_other_ruleset.py`:
  - `test-liga-unica` with the 8 lowest-id sample clubs plays to the end;
  - 14 rounds;
  - the final is 1st versus 2nd;
  - the relegated club is 8th;
  - its tiebreaker order is used (goal difference before wins);
  - no Mineiro-specific code path is hit (`season.py` has no ruleset id checks: a grep-based test).

### Implementation

- [ ] T041 [US3] Make sure every Mineiro-specific value comes from the ruleset (remove any leftover constants found by T040). Implement `participants` selection by `--participants`/state, and the `season rules [--validate PATH]` CLI with `list_rulesets` and `validate_ruleset` in the facade.

**Checkpoint**: two rulesets play, and broken rulesets are rejected clearly.

---

## Phase 6: User Story 4 - See the whole year (P4)

### Tests (first)

- [ ] T042 [P] [US4] Unit tests `core/tests/unit/test_calendar.py`:
  - `SeasonCalendar(year)` covers every day (365 or 366 days);
  - reserved windows are labelled on their days (fixed, per-year and Easter-based);
  - Carnival 2027 is labelled 6–10 February, with no state matches on 8–9 February;
  - Mineiro matchdays carry their match ids and stage events;
  - no Mineiro match falls on a `blocks = ["state"]` day.
- [ ] T043 [P] [US4] Contract test `core/tests/contract/test_cli_season_calendar.py`: `season calendar` prints 12 month summaries; `season calendar --month 2` lists every February day with matches and windows; `--month 13` exits 3.

### Implementation

- [ ] T044 [US4] Implement in `core/src/manager_core/competition/calendar.py`: reserved windows from `brazil.toml` (fixed and Easter-based) and the optional per-year file, `SeasonCalendar` and `CalendarDay`. Then the `season_calendar` facade function and the `season calendar` CLI. Note: the Easter computation and blocking windows are needed earlier by the scheduler (T020), so `easter(year)` and window resolution are written in T020 and reused here.

---

## Phase 7: Polish

- [ ] T045 [P] Update `docs/roadmap.md`: mark 002 as done, and add to the open items "confirmar no regulamento oficial FMF 2026: critérios de desempate, chaveamento das semifinais, participantes e datas do Troféu Inconfidência (5º–8º pulando semifinalistas vs. melhores 4 fora das semifinais)". Also note for spec 004: participants come from the previous season's outcomes.
- [ ] T046 [P] Update the `README.md` quick start with `season` commands.
- [ ] T047 Make sure `ruff check .`, `mypy` (strict) and the full pytest suite pass, and that the 1,000-season `slow` test passes locally.
- [ ] T048 Run [quickstart.md](quickstart.md) on Windows and note any deviations.
- [ ] T049 Open the PR `002-competitions-calendar` → `main` with a summary, test results and the quickstart check (description based on `specs/002-competitions-calendar/quickstart.md`).

---

## Dependencies & Execution Order

- Setup → Foundational → US1 → US2. US2 needs US1's season start.
- US3 needs US2: the test ruleset must play a full season.
- US4 needs US1 (dates), and can run in parallel with US2 and US3 after US1.
- Polish comes last.

## Parallel examples

```text
Foundational: T003 | T004 | T005, then T006 | T007 | T008 | T009
US1 tests:    T013 | T014 | T015 | T016 | T017
US2 tests:    T024 | T025 | T026 | T027 | T028 | T029 | T030 | T031
```

## Implementation Strategy

1. **MVP (stage 1)**: Setup + Foundational + US1. Stop: the owner reviews the draw, fixtures and dates.
2. **Stage 2**: US2, a full season played. Stop: the owner reviews tables, bracket and outcomes.
3. **Stage 3**: US3 + US4 + Polish → PR.
