# Research: Career Save and Game Loop (004)

Phase 0 decisions. Each entry: Decision / Rationale / Alternatives considered.

## R1. What a save stores: state snapshot plus played results

- **Decision**: a save stores:
  - the **world** at the start of the current season;
  - the **season definition**: ruleset TOML text, year, season master seed and participants;
  - every **played result** with its match report;
  - the **career** fields: name, master seed, user club, current date, last autosave date,
    pending stop;
  - the **history** of finished seasons.

  Loading rebuilds the season with `Season.start` from the stored definition, then replays it
  to the saved date. During the replay, a `RecordedProvider` returns the stored result for
  every match already played. It only falls back to the quick sim for matches after the save.
- **Rationale**:
  - **Fidelity (SC-001).** The season structure (draw, fixtures, dates) is deterministic from
    its definition, so rebuilding it is exact. Results are stored, not re-simulated, so a save
    survives a future change to the quick sim (a new `model.toml`). The owner's career does
    not change retroactively when the engine is recalibrated. FM behaves the same way.
  - **Self-contained.** Storing the ruleset text (not its id) keeps the save valid if the
    bundled ruleset file is edited later.
  - **No duplicated state.** Discipline (cards, suspensions) is *derived* from the stored
    match reports (R5), so it is never stored twice and cannot disagree with the results.
- **Alternatives**:
  - Pure event sourcing (seed + inputs only, re-simulate everything on load): the smallest
    files, but any engine change rewrites the owner's past. Rejected.
  - Serialising the whole `Season` object graph: brittle across code changes, and it
    duplicates derivable data. Rejected.

## R2. SQLite layout

- **Decision**: one SQLite file per save, using `sqlite3` from the standard library. Tables:
  - `meta(key, value)`: format version, core and Python versions, timestamps;
  - `career(...)`: a single row;
  - `world_files(name, text)`: the canonical 001 CSV texts of the world;
  - `season(...)`: a single row with the ruleset TOML, year, master seed and participants;
  - `results(match_id PRIMARY KEY, json)`;
  - `history(year PRIMARY KEY, json)`.

  `PRAGMA user_version` holds the save format version (1). Migrations are numbered functions
  `migrate_n_to_n1(conn)`.
- **World as CSV texts**: the world is written with 001's writer to a temporary folder, read as
  texts and stored. Loading writes them back and uses 001's reader. This reuses the
  round-trip-tested canonical format (001 SC) and its validation, instead of a second schema
  for clubs and players.
- **Atomic writes (SC-006)**: write to `<name>.sqlite.tmp`, `fsync`, then `os.replace` it over
  the target. A failure before the replace leaves the old file intact.
- **Alternatives**:
  - A JSON file per save: simpler, but the constitution names SQLite. It also gives queryable
    history for later UIs.
  - Normalised tables for players: the right choice once transfers and contracts arrive (v1).
    The migration path stays open (format version).

## R3. Result serialisation

- **Decision**: `Result` and `MatchReport` (and nested `Shootout`, events, stats and lineups)
  become JSON objects through explicit `to_dict` / `from_dict` functions in
  `career/codec.py`. Floats are rounded as in the report (xG to 2 decimal places). Every field
  is encoded explicitly, so a decoded report equals the original (a property test).
- **Rationale**: explicit codecs fail loudly on missing fields and survive field reordering;
  pickle would tie saves to class layouts and is unsafe.

## R4. The game loop and its stops

- **Decision**: `Career.continue_()` advances one day at a time with `Season.advance_to(day)`
  and stops at the first of:
  - **user match**: the next day has a match of the user club. The loop stops *before* that
    day (current date = day − 1), and the stop names the match. The next continue plays that
    day.
  - **event**: the day just played produced one of 002's competition events (`draw`,
    `stage_complete`, `qualified`, `paired`, `relegated`, `champion`, `title`).
  - **season end**: the season is complete.
- **Rationale**: this mirrors FM's "Continue" (spec decision 2). Stopping before the match day
  leaves the slot where spec 005 will put team selection.
- **Autosave**: after each day, if at least 7 days have passed since `last_autosave`, the
  career is written to the `autosave` slot (spec decision 7). Before the first match there are
  no days to play, so the first autosave happens a week into the season.

## R5. Discipline derived from match reports

- **Decision**: a `Discipline` ledger is rebuilt by walking the season's played matches in
  kick-off order. For each match, the players sent off (`red`, `second_yellow`) gain a
  one-match ban. Each `yellow` adds to the player's count, and on reaching 3 the player gains
  a one-match ban and the count resets to 0. A second yellow counts toward the red only
  (FR-009). Bans are served by the player's club's next match, in any stage of the same
  competition.
- **Applying bans**: before a match is played, the season asks the ledger which players of
  both clubs are suspended and passes them in `MatchContext.unavailable`. The quick sim builds
  a team sheet without them. Sheets are cached per (club, unavailable set), and the common
  empty set keeps the existing cache.
- **Rationale**: deriving keeps a single source of truth (R1). Walking about 60 matches per
  season is negligible.
- **Season end**: a new season starts with an empty ledger (FR-010).

## R6. Season rollover

- **Decision**: `rollover(world, season, rng)` returns the next season's world and
  participants, in the order of FR-011:
  1. **History**: record the season (outcome, final table and top scorers from 003).
  2. **Relegation and promotion**: the relegated clubs leave the participants, their players
     with them (M0 does not simulate Módulo II). Two promoted clubs are generated (R7).
  3. **Ageing**: `reference_date` moves one year forward. Ages are derived from birth dates,
     so every player ages.
  4. **Development**: for each player, a CA change is drawn from the age curve (R8) and
     applied by scaling the attributes of his natural positions' key weights, so the derived
     CA moves by about that amount. Potential caps growth.
  5. **Retirement** (R9).
  6. **Refill**: each club gets generated youngsters (R7) until it is back to 27 players. They
     are generated at the club's quality, with shirt numbers from the free ones.
  7. **Next season**: `Season.start` for year + 1 with a seed derived from the career master
     seed and the year (002 R4).
- **Determinism**: every step draws from `sub_seed(career_seed, f"rollover:{year}:{step}")`.

## R7. Generating clubs and youngsters

- **Decision**: expose 001's private generator pieces as `sample.generator.make_player(rng, pid,
  position, quality, reference_date, age=None)` and `make_club(...)`. This is a refactor:
  `generate()` keeps producing byte-identical sample data, and 001's sample tests guard that.
  - **Youngsters**: age 16–19, with the sample generator's potential headroom for that age.
  - **Promoted clubs**: names come from a fixed pool of fictional Minas towns, with ids made
    unique against existing clubs. They get the lowest tier's quality and reputation. Squads
    follow `SQUAD_SHAPE`.
  - **New player ids**: `p-NNNNNN`, continuing after the world's highest id.

## R8. Development curve (placeholder, FR-012)

- **Decision**: in `reference/career/development.toml`, a mean yearly CA change by age, with a
  standard deviation and a growth cap from potential:

  | Age | ≤ 20 | 21–23 | 24–27 | 28–30 | 31–32 | 33–34 | ≥ 35 |
  |---|---|---|---|---|---|---|---|
  | Mean ΔCA | +8 | +5 | +2 | 0 | −3 | −6 | −9 |

  The standard deviation is 4. Growth is capped at potential − CA, and decline is not capped.
- **Rationale**: the shape follows FM's common understanding (growth until about 24, plateau to
  about 30, decline after). It is a placeholder, only required to keep SC-004 (stable age mix)
  and a plausible squad strength. v1 replaces it with a calibrated development system
  (Constitution I).

## R9. Retirement (FR-013, spec decision 8)

- **Decision**: in `reference/career/retirement.toml`, a base probability by age, adjusted by
  personality and form:

  | Age | < 30 | 30–31 | 32 | 33 | 34 | 35 | 36 | 37 | ≥ 38 |
  |---|---|---|---|---|---|---|---|---|---|
  | Base p | 0 | 0.02 | 0.05 | 0.10 | 0.20 | 0.35 | 0.50 | 0.65 | 0.85 |

  `p = base · (1.5 if CA fell this year) · f(professionalism, ambition)`, with
  `f = clamp(1.3 − 0.03·(professionalism + ambition − 20), 0.6, 1.4)`. The result is capped
  at 0.95.
- **Rationale**: it is the player's decision, shaped by the hidden personality FM uses for
  career length (professionalism, ambition). The table aims at a retirement-age median of 34–36
  (SC-005), and a test checks it over 10 seasons.

## R10. CLI with state

- **Decision**:
  - `career` commands read and write save files in `--saves` (default `saves/` at the
    repository root, git-ignored).
  - The `season` views gain `--career NAME`: they load the save and show its current season
    instead of rebuilding from a seed. Without `--career`, 002's seed-based views still work
    (tests and quick looks).
- **Rationale**: it keeps 002 and 003 commands working, and it is the minimal stateful layer
  before 005's terminal UI.

## R11. Performance (SC-002)

- **Season replay on load**: about 0.3 s, mostly team sheets.
- **Writing a save**: dataset CSVs (about 330 players) plus about 60 results is roughly
  100–200 kB, written in ≤ 50 ms.
- **Full season from a new career**: about 1.5 s. That covers the cold sheets, 59 matches and
  about 9 weekly autosaves at ≤ 50 ms each, well under 5 s.
