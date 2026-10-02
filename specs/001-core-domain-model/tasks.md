---
description: "Task list for 001 Core Domain Model"
---

# Tasks: Core Domain Model

**Input**: Design documents from `specs/001-core-domain-model/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED. Constitution IV (test-first) applies. In each phase, write the test tasks first and confirm they fail before implementing.

**Organization**: tasks are grouped by user story (US1–US4 from spec.md), so each story can be
built and validated on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4. Setup, Foundational and Polish tasks carry no story label.
- Paths are relative to the repo root. The Python package root is `core/src/manager_core/` and
  the tests root is `core/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: project skeleton, tooling, and line-ending rules for byte-stable CSV.

- [ ] T001 Create the folder tree from plan.md "Source Code": `core/src/manager_core/{domain,ratings,io,sample,i18n,reference}/` with `__init__.py` in each package, `core/tests/{unit,contract,integration,fixtures/valid,fixtures/invalid,fixtures/excel_ptbr}/`, `data/sample/`
- [ ] T002 Create `core/pyproject.toml`:
  - project `manager-core`, version `0.1.0`, `requires-python = ">=3.12"`, **no runtime dependencies**;
  - optional `dev` extra = pytest, hypothesis, ruff, mypy;
  - setuptools src layout with package data `reference/*.csv`;
  - `[tool.ruff]` line-length 100, `[tool.mypy]` strict on `manager_core`, `[tool.pytest.ini_options]` testpaths `tests`.
- [ ] T003 [P] Set `__version__ = "0.1.0"` in `core/src/manager_core/__init__.py`, and add `core/src/manager_core/__main__.py` delegating to `cli.main()`
- [ ] T004 [P] Add `*.csv text eol=lf` to `.gitattributes` (research R4: committed CSVs must be byte-stable)
- [ ] T005 [P] Create a test helper `core/tests/conftest.py` with fixtures: `repo_root`, `sample_dir` (= `data/sample`), `fixtures_dir`, and a `tmp_dataset(dir)` copier

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: domain types, ratings needed by validation and display, the canonical CSV dialect,
the basic reader and writer, i18n, and the facade and CLI skeletons.

**⚠️ CRITICAL**: no user-story work can begin until this phase is complete.

### Tests first

- [ ] T006 [P] Unit tests `core/tests/unit/test_attributes.py`:
  - exactly 60 attributes, with 14 technical, 14 mental, 8 physical, 11 goalkeeping and 13 hidden, in FM order (data-model.md);
  - values "1–20" enforced by the constructor (raises on 0 or 21);
  - hidden defaults are 10, "except dirtiness 8, injury_proneness 8 and controversy 6".
- [ ] T007 [P] Unit tests `core/tests/unit/test_positions.py`:
  - the 14 codes in FM order "GK, DL, DC, DR, WBL, WBR, DM, ML, MC, MR, AML, AMC, AMR, ST", and the line of each;
  - band boundaries: Natural 18–20, Accomplished 15–17, Competent 12–14, Unconvincing 9–11, Awkward 5–8, Ineffectual 1–4;
  - familiarity factor anchors 20→1.00, 18→0.99, 15→0.96, 12→0.90, 9→0.82, 5→0.70, 1→0.55, with linear interpolation and monotonicity.
- [ ] T008 [P] Unit tests `core/tests/unit/test_ability.py`:
  - CA formula from research R8 on hand-computed cases;
  - clamp to 1–200;
  - hypothesis property: raising any visible attribute never lowers CA;
  - `best_position` only considers familiarity ≥ 15, with ties broken by FM position order.
- [ ] T009 [P] Unit tests `core/tests/unit/test_suitability.py`:
  - weighted mean using `reference/position_weights.csv`;
  - an equally-attributed Natural player outranks an Unconvincing one;
  - mirrored positions (DR/DL, WBR/WBL, MR/ML, AMR/AML) give equal results for mirrored players.
- [ ] T010 [P] Unit tests `core/tests/unit/test_dialect.py` for the canonical writer:
  - UTF-8 with BOM, `;` separator, LF, ISO dates, plain integers, rows sorted by key;
  - byte-identical output on repeated writes.
- [ ] T011 [P] Contract test `core/tests/contract/test_csv_format.py`:
  - every file and column name, and the column write order, exactly as in contracts/csv-format.md v1.0;
  - the attributes.csv columns are derived from `ATTRIBUTE_GROUPS` (single source of truth).
- [ ] T012 [P] Contract test `core/tests/contract/test_facade.py`: `manager_core.api` exposes the functions and parameter names listed in contracts/facade.md

### Implementation

- [ ] T013 [P] Implement `core/src/manager_core/domain/attributes.py`:
  - frozen, slotted `Attributes` with 60 explicit `int` fields;
  - `AttributeGroup` enum and `ATTRIBUTE_GROUPS` (FM order);
  - `HIDDEN_DEFAULTS`;
  - range check 1–20 in `__post_init__`;
  - `visible_for(is_goalkeeper)`: the display groups per data-model.md (GK reduced technical set: first touch, free kicks, passing, penalty taking, technique).
- [ ] T014 [P] Implement `core/src/manager_core/domain/positions.py`:
  - `Position` enum (FM order) and `Line`;
  - `FamiliarityBand` and `band_for(value)`;
  - `familiarity_factor(value)` with the R7 anchors;
  - `PositionFamiliarity` (immutable mapping, missing codes default to 1, values 1–20, `natural_positions()` for ≥ 15).
- [ ] T015 [P] Implement `core/src/manager_core/domain/club.py`:
  - frozen `Club` with the fields of data-model.md "Club", using the "Rules" column as constructor invariants: abbreviation "exactly 3 uppercase letters", colours `#RRGGBB`, capacity 500–250,000, reputation 1–20;
  - `ExternalRef(source, source_id)`.
- [ ] T016 [P] Implement `core/src/manager_core/domain/player.py`:
  - frozen `Player` with the data-model.md "Player" fields: nationalities 1–3, height 150–210, weight 50–110, feet 1–20 with "max(left, right) ≥ 15", PA 1–200;
  - `age(reference_date)` derived, never stored.
- [ ] T017 [P] Implement `core/src/manager_core/domain/squad.py`:
  - frozen `SquadMembership`: shirt number 1–99 or None, money fields ≥ 0, currency required when a money field is set.
- [ ] T018 [P] Implement `core/src/manager_core/domain/formation.py`:
  - `FormationSlot(index, position, x_m 0–105, y_m 0–68)` and `Formation`, requiring "exactly 11 slots, exactly one GK";
  - `load_catalogue()` reading `reference/formations.csv`.
- [ ] T019 [P] Create reference data:
  - `core/src/manager_core/reference/position_weights.csv`, containing exactly the table in contracts/csv-format.md, with mirrored positions expanded;
  - `core/src/manager_core/reference/formations.csv`, with 4-4-2, 4-3-3, 4-2-3-1, 3-5-2 and 5-3-2 using the prototype's metre coordinates (`prototype/manager/tactics.py`);
  - `core/src/manager_core/reference/nations.csv` (`code;name_pt;confederation`): FIFA trigrams for all CONMEBOL members, the main UEFA nations including ENG/SCO/WAL/NIR, CONCACAF majors, and common African and Asian origins.
- [ ] T020 Implement `core/src/manager_core/ratings/suitability.py` (depends on T013, T014, T019):
  - `base(player, position)` as a weighted mean from position_weights.csv;
  - `suitability(player, position) = base × familiarity_factor`.
- [ ] T021 Implement `core/src/manager_core/ratings/ability.py` (depends on T020):
  - `current_ability(player)`, `best_position(player)` and `is_goalkeeper(player)`, exactly per research R8: CA = round(1 + (S − 1) × 199 / 19), S = 0.85 × max natural base + 0.15 × mean of relevant visible attributes, clamped to 1–200.
- [ ] T022 Implement `core/src/manager_core/domain/dataset.py`:
  - `Dataset` (format_version, reference_date, fictional, tool, tool_version, seed, notes, sources, clubs, players, memberships, record_flags);
  - `Source` and `RecordFlag` (flags: hidden_defaulted, potential_defaulted, manually_edited, added_manually);
  - all collections exposed in sorted-id order;
  - queries `squad(club_id)` and `free_agents()`.
- [ ] T023 [P] Implement `core/src/manager_core/i18n/__init__.py` (`t(key, **params)`, raising `KeyError` on a missing key in tests) and `core/src/manager_core/i18n/pt_BR.py`, with the catalogue for CLI labels, attribute names in Portuguese (FM-BR naming, e.g. "Finalização", "Desarme"), band names and position names.
- [ ] T024 Implement `core/src/manager_core/io/schema.py`:
  - per-file column specs (name, type, required, range) for all files in contracts/csv-format.md;
  - attributes.csv columns generated from `ATTRIBUTE_GROUPS`;
  - `FORMAT_VERSION = "1.0"`, `SUPPORTED_MAJOR = 1`.
- [ ] T025 Implement `core/src/manager_core/io/dialect.py`:
  - canonical `write_table(path, columns, rows)`: UTF-8 BOM, `;`, LF, ISO dates, sorted;
  - `read_table(path)`: in this phase it handles only canonical files (the Excel tolerance comes in US2), returning raw string rows with 1-based row numbers.
- [ ] T026 Implement `core/src/manager_core/io/validate.py` (skeleton):
  - `Issue(code, severity, file, record_id|row, field, value, message)` and `ValidationReport` (ordered issues, `ok`);
  - structural checks only: E001 missing file, E025 missing column, E004 integer parse/range, E002/E003 ids.
  - The full catalogue comes in US2.
- [ ] T027 Implement `core/src/manager_core/io/reader.py`: `load(path) -> LoadResult(report, dataset|None)`. It reads all tables, validates them, and only builds domain objects if `report.ok` (all-or-nothing). Hidden defaults are applied with the `hidden_defaulted` flag, and an empty PA becomes CA with the `potential_defaulted` flag.
- [ ] T028 Implement `core/src/manager_core/io/writer.py`: `write(dataset, path) -> ExportSummary` writing every file of contracts/csv-format.md through `dialect.write_table`, with the column order exactly as in the contract.
- [ ] T029 Implement the facade skeleton `core/src/manager_core/api.py`:
  - `load_dataset`, `validate_dataset`, `export_dataset`;
  - `NotFoundError(kind, id)`;
  - signatures per contracts/facade.md, with the remaining functions raising `NotImplementedError`.
- [ ] T030 Implement the CLI skeleton `core/src/manager_core/cli.py`:
  - argparse groups `data`, `sample`, `club`, `player`, `position`, `lineup`, `formation`;
  - global `--data` (default `data/sample`), resolved from the repo root;
  - exit codes 0/1/2/3 per contracts/cli.md;
  - all text through `t()`.

**Checkpoint**: the domain, ratings, canonical I/O, facade and CLI skeletons all pass their
tests. User stories can start.

---

## Phase 3: User Story 1 - Explore a ready-made football world (Priority: P1) 🎯 MVP

**Goal**: a committed, deterministic, fictional 12-club Mineiro-style world that the owner can
browse from the CLI with FM-style profiles.

**Independent Test**:
- `python -m manager_core club list`, then `club squad` and `player show` on `data/sample/`.
- The world loads with zero errors and zero W001.
- Regenerating it is byte-identical.
- Attribute coherence holds (SC-005).

### Tests for User Story 1 (write first, must fail)

- [ ] T031 [P] [US1] Integration test `core/tests/integration/test_sample_world.py`:
  - `data/sample/` loads with `report.ok` and no W001;
  - 12 clubs in tiers 3 strong / 5 mid / 4 small (by reputation);
  - each club has 25–30 players, "at least 3 goalkeepers and at least 2 natural players for each line";
  - ages roughly 17–37;
  - the provenance marks `fictional=true` and records the generator version and seed;
  - no real club names: assert against a denylist of current Mineiro clubs (Atlético, Cruzeiro, América, Tombense, Athletic, Ipatinga, Pouso Alegre, Democrata, Villa Nova, URT, Caldense, Uberlândia, Itabirito, North, Betim, Patrocinense).
- [ ] T032 [P] [US1] Integration test `core/tests/integration/test_sample_determinism.py`: generating with seed 20261002 into a temp dir is byte-identical to `data/sample/` for every file (SC-002), and a different seed differs.
- [ ] T033 [P] [US1] Integration test `core/tests/integration/test_sample_coherence.py`:
  - for each position, the mean of its key attributes among natural players exceeds the mean among other outfield players by ≥ 2;
  - goalkeepers' mean goalkeeping attributes exceed outfield players' by ≥ 8 (SC-005);
  - hidden attributes are not constant (W005 never raised);
  - strong-tier average CA > mid > small.
- [ ] T034 [P] [US1] Contract test `core/tests/contract/test_cli_explore.py`:
  - `club list`, `club squad <id> --sort position|ca|age|number` and `player show <id> [--hidden]` exit 0, with the columns from contracts/cli.md;
  - hidden attributes and PA appear only with `--hidden`;
  - an unknown id exits 3;
  - duplicate display names in a squad are disambiguated (shirt number or birth year).

### Implementation for User Story 1

- [ ] T035 [P] [US1] Create `core/src/manager_core/sample/names.py`:
  - 12 curated fictional club identities: fictional Minas Gerais-style towns, with names, short names, abbreviations, UF = MG, colours, stadium names and capacities, founded years, and reputation per tier (strong 13–15, mid 9–11, small 6–8);
  - pools of common Brazilian first names, surnames and football nicknames.
- [ ] T036 [US1] Implement `core/src/manager_core/sample/generator.py`:
  - `generate(seed=20261002) -> Dataset`, using its own `random.Random(seed)`;
  - 27 players per club (3 GK, ≥ 2 natural per line);
  - tier key-attribute means about 13.5, 10 and 8, with per-player spread;
  - position-archetype templates;
  - secondary positions (e.g. DL→WBL 17);
  - height and weight by position;
  - feet about 75% right, 20% left, 5% two-footed;
  - hidden attributes N(10, 3.5), clamped;
  - PA = CA + age-dependent headroom;
  - unique ids `p-000001…`;
  - reference date 2027-01-01;
  - provenance: fictional, tool `manager_core.sample`, version and seed.
  - Iterate only in sorted or fixed order (Constitution II).
- [ ] T037 [US1] Facade: implement `generate_sample`, `list_clubs` (ClubSummary with squad size and average CA), `squad` (SquadEntry: number, display name, age, best position, band, suitability, CA, with sorts position/ca/age/number) and `player_profile` (FM-grouped visible attributes, hidden attributes and PA only when `include_hidden`) in `core/src/manager_core/api.py`.
- [ ] T038 [US1] CLI: implement `sample generate [--seed] [--out]`, `club list`, `club squad` and `player show [--hidden]` in `core/src/manager_core/cli.py`. Render text tables using pt-BR labels via `t()`, with display-name disambiguation.
- [ ] T039 [US1] Generate and commit the sample world: run `python -m manager_core sample generate` to write `data/sample/*.csv`, then check that T031–T033 pass and adjust the generator (not the data) until they do.

**Checkpoint**: US1 is fully functional. The MVP can be demonstrated.

---

## Phase 4: User Story 2 - Import a curated dataset safely (Priority: P2)

**Goal**: full validation catalogue, provenance enforcement, format versioning and tolerance
for files saved by pt-BR Excel.

**Independent Test**: `data validate` accepts `fixtures/valid/minimal` and rejects every
`fixtures/invalid/E0xx_*` with the expected code, file, record and field. The `excel_ptbr`
fixture loads with W008/W009 as appropriate.

### Tests for User Story 2 (write first, must fail)

- [ ] T040 [P] [US2] Create `core/tests/fixtures/valid/minimal/`: a hand-written canonical dataset of 2 clubs × 12 players, with provenance, one free agent and one player with no hidden columns (expects `hidden_defaulted`).
- [ ] T041 [P] [US2] Create one invalid fixture folder per error code: `core/tests/fixtures/invalid/E001_missing_file/` … `E033_bad_encoding/`. Each one is a copy of `valid/minimal` with exactly one defect, plus an `expected.txt` holding `code;file;record_id;field`. Cover all codes in data-model.md: E001–E005, E010, E011, E013–E025, E030–E033 (SC-004: ≥ 15).
- [ ] T042 [P] [US2] Create `core/tests/fixtures/excel_ptbr/`: `valid/minimal` re-encoded as Excel pt-BR would save it, with `;`, a BOM, CRLF, `DD/MM/YYYY` dates, `15.000.000` money values, one file in Windows-1252, and one extra unknown column.
- [ ] T043 [P] [US2] Contract test `core/tests/contract/test_validation_catalogue.py`:
  - parametrised over `fixtures/invalid/*`;
  - load fails, nothing is constructed, and the report contains the issue from `expected.txt`;
  - a fixture with 3 independent defects reports all 3 in one pass;
  - issues are ordered by file, row, then field.
- [ ] T044 [P] [US2] Integration test `core/tests/integration/test_warnings.py` covering W001–W009 on dedicated small fixtures: the dataset loads and the warnings are listed.
- [ ] T045 [P] [US2] Integration test `core/tests/integration/test_excel_ptbr.py`: the `excel_ptbr` fixture loads `ok`, with W007/W008/W009, and its values equal `valid/minimal`'s exactly.
- [ ] T046 [P] [US2] Integration test `core/tests/integration/test_format_version.py`: version 1.0 is accepted, `2.0` is refused with E031 and a clear pt-BR message, and a garbage version gives E030.
- [ ] T047 [P] [US2] Performance test `core/tests/integration/test_performance.py`: loading and validating `data/sample/` takes < 2 s (SC-001). Mark it `slow`, but run it in CI.

### Implementation for User Story 2

- [ ] T048 [US2] Extend `core/src/manager_core/io/dialect.py` with tolerant reading per research R4:
  - separator sniffing (`;` or `,`);
  - UTF-8 with or without BOM, falling back to Windows-1252 (raising W008), and E033 if neither works;
  - CRLF and LF;
  - trimmed cells;
  - `DD/MM/YYYY` dates (W009);
  - pt-BR integer grouping `^\d{1,3}(\.\d{3})+$`;
  - booleans `true/false/sim/não`;
  - unknown columns raise W007.
- [ ] T049 [US2] Complete `core/src/manager_core/io/validate.py` with every rule in the data-model.md catalogue:
  - E005 text length, E010 date, E011 age 14–45 at the reference date, E013/W006 nation codes against `nations.csv`, E014 feet, E015 PA < CA, E016 no position ≥ 15, E017 unknown reference, E018 duplicate membership, E019 duplicate shirt number, E020 abbreviation, E021 UF when country = BRA, E022 colour, E023 currency, E024 attributes/positions coverage, E030/E031 version, E032 no source;
  - warnings W001–W005.
  - Collect all issues in one pass, with messages via `t()` in pt-BR.
  - Keep validation linear in record count (plan: practical for about 50k players).
- [ ] T050 [US2] Facade and CLI: implement `validate_dataset` in `core/src/manager_core/api.py`, and `data validate <dir>` in `core/src/manager_core/cli.py`. It prints errors, then warnings, grouped by file with record and field, then a summary line, and exits 1 on errors.

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Find who can play where (Priority: P3)

**Goal**: rank a squad for any position and suggest the optimal XI for any catalogue formation.

**Independent Test**: on hand-built fixtures, the ranking order and the best XI match known
answers (SC-006). On the sample world, the CLI commands return sensible results.

### Tests for User Story 3 (write first, must fail)

- [ ] T051 [P] [US3] Unit tests `core/tests/unit/test_lineup.py`:
  - bitmask-DP best XI equals the brute-force optimum on 20 random small squads (12–14 players, seeded) (SC-006);
  - each player is used at most once;
  - exactly one player fills the GK slot;
  - deterministic tie-break (higher total, then lexicographically smaller tuple of player ids);
  - a squad with no fit GK still returns 11 players with the `outfield_in_goal` flag;
  - a 27-player squad runs in < 0.5 s.
- [ ] T052 [P] [US3] Contract test `core/tests/contract/test_cli_lineup.py`:
  - `position rank <club> DC`, `lineup suggest <club> --formation 4-3-3` and `formation list` exit 0 with the contracts/cli.md columns;
  - an unknown position, club or formation exits 3.

### Implementation for User Story 3

- [ ] T053 [US3] Implement `core/src/manager_core/ratings/lineup.py`:
  - `rank_for_position(players, position)`, sorted by suitability desc, then id;
  - `best_xi(players, formation) -> Lineup(assignments, total, flags)` via bitmask DP over the 11 slots per research R9.
- [ ] T054 [US3] Facade: implement `rank_for_position`, `suggest_lineup` and `list_formations` in `core/src/manager_core/api.py`.
- [ ] T055 [US3] CLI: implement `position rank`, `lineup suggest [--formation]` and `formation list` in `core/src/manager_core/cli.py`.

**Checkpoint**: US1–US3 work independently.

---

## Phase 6: User Story 4 - Edit and round-trip data (Priority: P4)

**Goal**: lossless export, and detection of manual edits through integrity hashes.

**Independent Test**: export and re-import of the sample world is identical. Editing one
attribute flags exactly that player as `manually_edited`, and only that value differs.

### Tests for User Story 4 (write first, must fail)

- [ ] T056 [P] [US4] Property test `core/tests/integration/test_roundtrip.py`:
  - hypothesis-generated small datasets, plus the sample world: export → import → equal datasets, including provenance, external refs and record flags (SC-003);
  - exporting twice is byte-identical.
- [ ] T057 [P] [US4] Integration test `core/tests/integration/test_manual_edits.py`:
  - change one attribute in an exported folder → re-import flags exactly that player `manually_edited`;
  - add a new player → `added_manually`;
  - re-save the folder through the `excel_ptbr` transformation (re-format only) → **no** edit flags;
  - no `integrity.csv` → no edit flags.

### Implementation for User Story 4

- [ ] T058 [US4] Implement `core/src/manager_core/io/integrity.py`:
  - a canonical per-record serialisation covering the record's rows across all files (normalised values, not bytes), with SHA-256;
  - `compute(dataset)` and `detect_edits(dataset, integrity_rows) -> list[RecordFlag]`.
- [ ] T059 [US4] Wire integrity into I/O: `writer.write` writes `integrity.csv` and `record_flags.csv`, and `reader.load` applies `detect_edits` when `integrity.csv` is present. Files: `core/src/manager_core/io/writer.py` and `core/src/manager_core/io/reader.py`.
- [ ] T060 [US4] Facade and CLI: complete `export_dataset`, and `data export <src> <dst>`, which prints the records written and the flags raised, in `core/src/manager_core/api.py` and `core/src/manager_core/cli.py`.

**Checkpoint**: all four user stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T061 [P] Add CI `.github/workflows/ci.yml`: on pull_request and push to main, a matrix of {windows-latest, ubuntu-latest} × {3.12, 3.14}, running `pip install -e "core[dev]"`, `ruff check core`, `mypy core/src` and `pytest core/tests` (research R15)
- [ ] T062 [P] Update `README.md` with how to install and run the CLI (link to quickstart), and update the status line
- [ ] T063 [P] Update `docs/roadmap.md`: mark 001 as done, with a link to the spec
- [ ] T064 Make `ruff check core` and `mypy core/src` (strict) pass with no ignores beyond those justified in a comment
- [ ] T065 Run every step of [quickstart.md](quickstart.md) on Windows, including the manual Excel round-trip (step 6), and note any deviations in the PR description
- [ ] T066 Open the PR `001-core-domain-model` → `main` with a summary, test results and a quickstart check. No calibration report is needed (no simulation system touched).

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (T001–T005) comes first.
- Foundational (T006–T030) depends on Setup and **blocks all stories**.
- US1 (T031–T039) depends on Foundational. **MVP.**
- US2 (T040–T050) depends on Foundational. It does not need US1: its fixtures are hand-built.
- US3 (T051–T055) depends on Foundational. Its CLI demo uses the sample world (US1), but its
  tests use hand-built squads.
- US4 (T056–T060) depends on Foundational. T057's Excel re-format case reuses the US2 tolerant
  reader (T048).
- Polish (T061–T066) comes after the desired stories.

### Within Foundational

T013–T019 run in parallel. Then T020 → T021. T022 needs T013–T018. T024 → T025 → T026 → T027 and
T028. T029 → T030.

### Within each story

Tests first, and they must fail. Then data or reference files, then logic, then the facade,
then the CLI.

## Parallel examples

```text
# Foundational tests together:
T006 test_attributes.py | T007 test_positions.py | T008 test_ability.py | T009 test_suitability.py | T010 test_dialect.py | T011 test_csv_format.py | T012 test_facade.py

# Foundational domain modules together:
T013 attributes.py | T014 positions.py | T015 club.py | T016 player.py | T017 squad.py | T018 formation.py | T019 reference CSVs

# US2 fixtures and tests together:
T040 valid/minimal | T041 invalid/* | T042 excel_ptbr | T043–T047 tests
```

## Implementation Strategy

1. **MVP**: Setup → Foundational → US1. Stop and validate: browse the sample world from the
   CLI and check determinism and coherence.
2. **US2**: safe import, needed before any real data (spec 011) can arrive.
3. **US3**: who-can-play-where and the best XI, needed by spec 005.
4. **US4**: Excel round-trip and edit audit trail.
5. **Polish**: CI, docs, quickstart run, PR.

Commit after each task or logical group, on branch `001-core-domain-model`.
