# Tasks: Real Data for Minas Gerais Clubs

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/realdata-cli.md](contracts/realdata-cli.md),
[quickstart.md](quickstart.md)

**Tests**: required (Constitution IV). They use fictional HTML fixtures and the fictional sample,
never the network or private data.

## Phase 1: Setup

- [x] T001 Create the `manager_core.realdata` package skeleton (`__init__.py`, `__main__.py` with argparse subcommands `collect`, `build`, `report`, `correct` and `check-public` per contracts/realdata-cli.md) in core/src/manager_core/realdata/.
- [ ] T002 [P] Lay out the private repository: `inputs/mineiro.toml` (the 12 Módulo I clubs of 2026 with `club_id`, `division`, `module`, `ogol_id`, `wikipedia_title` and owner `colors` as `#RRGGBB`), `.gitattributes` and a README, in C:\Users\DE0191297\Documents\manager-data (private repository, never the public one).

## Phase 2: Foundational

- [x] T003 Write tests for the fetcher with a fake opener. It must:
  - obey robots.txt (refuse disallowed paths);
  - wait at least 4 s per host, with an injectable clock;
  - send the honest user agent;
  - read from the cache without fetching on a second call;
  - honour `--refresh`;
  - stop a source on 403 or 429;
  - log every fetch.

  In core/tests/unit/test_realdata_fetch.py.
- [x] T004 Implement the fetcher (R2) with urllib.request and urllib.robotparser, a gzipped cache `cache/<source>/<sha1>.html.gz` and `cache/<source>/log.csv` (`url;fetched_at;status;bytes`), in core/src/manager_core/realdata/fetch.py.
- [x] T005 [P] Write tests and implement the public-repo guard (R7):
  - every tracked `dataset.csv` declares `fictional=true`;
  - no tracked file matches the private layout (`cache/`, `corrections.csv`, `datasets/`);
  - the CLI refuses a data repository inside the public repository.

  In core/tests/integration/test_no_real_data.py and core/src/manager_core/realdata/guard.py.

## Phase 3: User Story 1 - Choose the sources with evidence (P1)

**Goal**: the owner chooses sources from a complete survey.

**Independent test**: research.md R1 covers every candidate with every FR-001 field, and the
owner's choices are recorded.

- [x] T006 [US1] Survey Wikipedia, ogol, Brasileirinho FC, CBF BID, FootyStats, ESPN, SofaScore, FBref, Transfermarkt and FM mods (coverage, freshness, terms and robots, fields) in specs/011-real-data/research.md.
- [x] T007 [US1] Record the owner's decisions (synthesis model, Minas first, ogol used gently) in specs/011-real-data/spec.md.
- [ ] T008 [US1] Close the open ⏳ items once collection shows real coverage: Mineiro squads on ogol for all 12 clubs, Wikipedia infobox colours or the owner's colours. Record them in specs/011-real-data/research.md.

## Phase 4: User Story 2 - Play with the real Mineiro clubs (P1)

**Goal**: real Módulo I clubs and squads load and play.

**Independent test**: build from fixtures or the cache. The dataset validates (001), and a career
starts and plays a match day with a real club.

- [ ] T009 [P] [US2] Add fictional HTML fixtures: an ogol club squad page, two ogol player pages (one with market value, one without) and a Wikipedia club page, mirroring the real pages' structure with invented names. In core/tests/fixtures/realdata/.
- [x] T010 [P] [US2] Write tests for the ogol parsers. The squad page gives player ids, shirt numbers, positions, names, ages, nationalities, games and values. The player page gives birth date, height, foot, positions, and minutes, goals and assists by season. In core/tests/unit/test_realdata_ogol.py.
- [x] T011 [US2] Implement the ogol parsers with html.parser, returning RawClub and RawPlayer (data-model.md), in core/src/manager_core/realdata/sources/ogol.py.
- [ ] T012 [P] [US2] Write tests and implement the Wikipedia parser (club infobox: name, city, stadium, capacity, founded; competition final table) in core/tests/unit/test_realdata_wikipedia.py and core/src/manager_core/realdata/sources/wikipedia.py.
- [ ] T013 [US2] Write tests and implement the merge (R3):
  - ids `p-og<id>`, and club slugs;
  - precedence: correction, then ogol, then Wikipedia;
  - disagreements listed;
  - name collisions resolved by id, never merged;
  - `sources.csv` and `external_refs.csv` rows.

  In core/tests/unit/test_realdata_merge.py and core/src/manager_core/realdata/merge.py.
- [x] T014 [US2] Implement `build`: cache, then parse, merge, synthesise (T017), correct (T021), write with the 001 writer and validate. Add `import-report.md` (FR-008, per club). Write a test: an integration build from fixtures gives a valid dataset that a career can load and play. In core/src/manager_core/realdata/build.py and core/tests/integration/test_realdata_build.py.
- [x] T015 [US2] Implement `collect` for ogol and Wikipedia over `inputs/mineiro.toml`: club pages, then each squad player's page. Run it once for Módulo I at a 4 s or longer pace, into the private cache. In core/src/manager_core/realdata/__main__.py.

## Phase 5: User Story 3 - Believable ability (P2)

**Goal**: every player gets an overall level and attributes from public signals only.

**Independent test**: on the sample and the fixtures:
- distributions and position profiles are right;
- output is deterministic per player id;
- the Módulo I build reaches SC-003.

- [ ] T016 [P] [US3] Write the model parameters (club baselines by division; offsets for minutes share, log value, age and output per 90; the CA-to-attribute-mean mapping; position profiles; age curves; PA headroom) in core/src/manager_core/reference/synthesis/model.toml and profiles.toml.
- [x] T017 [US3] Write tests and implement the synthesis model (R4). The tests cover:
  - attributes are in 1–20;
  - a goalkeeper's profile against a winger's;
  - age curves;
  - determinism by player id;
  - the confidence levels `high`, `medium` and `low`, with their reasons;
  - no input field named for another game's rating.

  In core/tests/unit/test_realdata_synthesis.py and core/src/manager_core/realdata/synthesis.py.
- [x] T018 [US3] Add the SC-003 check (revised 2026-10-18, owner decision): the `strength` command simulates the Mineiro and sets each club's title share against the real champions of 2007-2026. Tune `model.toml` until the top-two and top-three shares are within 10 points. In core/src/manager_core/realdata/strength.py.

## Phase 6: User Story 4 - Corrections stick (P2)

**Goal**: owner corrections win, survive re-imports, and form the field-level audit trail.

**Independent test**: correct, rebuild, and the correction remains. The report lists it, and the
record carries `manually_edited`.

- [x] T019 [P] [US4] Write tests for corrections (R5). They cover:
  - apply last;
  - survive a rebuild with changed source values ("source changed under a correction" is
    reported);
  - a correction on a vanished record is kept and reported;
  - `manually_edited` in `record_flags.csv`;
  - the file is append-only (`record_type;record_id;field;old_value;new_value;date;note`).

  In core/tests/unit/test_realdata_corrections.py.
- [x] T020 [US4] Implement corrections in core/src/manager_core/realdata/corrections.py.
- [x] T021 [US4] Implement the `correct` command, which appends a row with the current value as `old_value` and today's date, in core/src/manager_core/realdata/__main__.py.

## Phase 7: User Story 5 - Módulo II and Excel (P3)

**Goal**: Módulo II coverage, and pt-BR Excel round trips.

**Independent test**: a Módulo II build reports gaps per club. A file re-saved the way Excel saves
it loads unchanged.

- [x] T022 [P] [US5] Write tests and implement pt-BR Excel tolerance (R6): byte-order mark, UTF-8 or Windows-1252, `;` or `,` separators, decimal commas, `dd/mm/yyyy` dates, stray spaces. Reading only; writing stays canonical. In core/tests/unit/test_io_excel_tolerance.py and core/src/manager_core/io/dialect.py.
- [ ] T023 [US5] Add the Módulo II clubs to `inputs/mineiro.toml`, collect and build. Report gaps per club. In C:\Users\DE0191297\Documents\manager-data.

## Phase 8: Polish

- [ ] T024 Write docs: README (real data: private repository, CLI, owner review), roadmap (011 status), and quickstart verification run.
- [ ] T025 Run the full suites (core, client), plus ruff and mypy. Open the PR and ask the owner before merging.

## Progress notes (2026-10-16)

- **`build` works on the real Módulo I cache** (T014, offline, byte-stable): 12 clubs and 549
  players, 0 validation errors and 0 warnings. A career on it starts, and a whole Mineiro plays
  through (Cruzeiro x North at the Mineirão to open). Squad strength (mean CA of the top 16):
  Cruzeiro 131, Atlético 129, Athletic 108, América 106, the rest 76-85.
- **Squads are the 2026 season lists, departed players included** (my call, his rule; to confirm
  in review). In October a state-league-only club's page shows only the few players still under
  contract (Itabirito 4, North 3, URT 5 active), but its whole season list (29-41) is the Mineiro
  squad, and the game plays the Mineiro. A player listed at several clubs plays for the one he
  is still at, or, at none, for the one he played most games for that season. The import report
  lists the moves.
- Players outside the 001 ages (14-45) are left out and listed in the report (one: a 53-year-old
  veteran at Democrata).
- The parsers gained:
  - the stadium and its capacity (from the club page, so Wikipedia is not needed for the MVP);
  - the height under "Altura" alone, and the weight under "Peso";
  - the dual nationality, which ogol runs together ("Brasil Itália"), matched longest first;
  - the team path of each career line (own-club links carry no id);
  - the last card row, which no longer runs to the end of the page.
- `reference/nations.csv` gains Guiné and São Tomé e Príncipe. The 001 flags gain
  `synthesis_confidence` and `incomplete`.
- `inputs/mineiro.toml` (private) gains short names and abbreviations (Pouso Alegre is POU, not
  PAL). These are to confirm in review.
- **Gap for T018 (SC-003)**: over 20 simulated Mineiros the order is right (the big four on top),
  but the spread is flat. Atlético, Cruzeiro and Athletic win 5 each, and a state-league club
  wins about 1 in 7. In reality the big two win nearly every year. Next: T018 (tune the
  synthesis against the real table), the Wikipedia parser (T012), corrections (T019-T021).

## Progress notes (2026-10-18)

- **SC-003 revised** (owner decision): one real season is too noisy to rank by (the game's own
  strength ranking reaches Spearman 0.7 against a simulated first phase only 20% of the time), so
  the check is the simulated title share against the real champions of 2007-2026 (ogol: Atlético
  12, Cruzeiro 7, América 1).
- **Synthesis 0.2**: division baselines A 150, B 100, C 88, D 78, none 70. Over 100 Mineiros the
  top two win 94% (real 95%) and the top three 96% (real 100%); goals per match are unchanged.
  Research R4 has the fit table.
- **Bug fixed**: the live pages write values as "3.00 M €", which was read as 300 M (the dot taken
  for a thousands separator). Values are now right (Cruzeiro's median €3 M).
- Club market values cannot separate the Série B clubs, and most smaller clubs have none.
- **Corrections (T019-T021)**: `corrections.csv` (private, append-only) is applied last, on the
  written 001 tables by column name, so any player, club, squad, attribute or position field can
  be corrected and the game's validator checks it. Each corrected record gets `manually_edited`
  with the fields. A source change under a correction, a gone record or an unknown field is kept
  and listed in the report under "Corrections to review". `correct` reads the current value from
  the built dataset, tries the change on a copy, and appends only what the game accepts.
- **Excel tolerance (T022)**: a dataset re-saved by pt-BR Excel loads to the identical dataset:
  Windows-1252 or UTF-8, `;` or `,` (from the header), quoted cells, CRLF, stray spaces,
  dd/mm/yyyy dates and VERDADEIRO/FALSO. E033 now means neither UTF-8 nor Windows-1252 (its
  fixture uses an unassigned byte). Writing stays canonical.
- Next: Wikipedia parser (T012).

## Dependencies

- Setup (T001–T002), then Foundational (T003–T005), then the stories.
- US2's build (T014) needs T017 (synthesis) and T020 (corrections) to be complete. Until then it
  runs with stubs.
- US3 tuning (T018) needs the real Módulo I cache (T015).
- US5 is independent of US3 and US4.

## Parallel examples

- T009, T010 and T012 together (fixtures and parser tests).
- T016 and T019 together (model parameters and correction tests).
- T005 and T022 at any time.

## Implementation strategy

MVP is US2 (real clubs and squads load and play) with a simple synthesis model. Then refine the
model to SC-003 (US3), corrections (US4), and Módulo II and Excel (US5).
