# Research: Competitions and Calendar (002)

Phase 0 decisions. Each entry: Decision / Rationale / Alternatives considered.

## R1. Ruleset file format

- **Decision**: one **TOML** file per ruleset in `core/src/manager_core/reference/competitions/`
  (`mg-modulo-i-2026.toml`, `test-liga-unica.toml`), read with the standard library `tomllib`.
  The full schema is in [contracts/ruleset-format.md](contracts/ruleset-format.md).
- **Rationale**: rulesets are nested (stages, entrants, tiebreakers) and written by hand. TOML
  allows comments, which we need to cite the FMF regulation next to each rule, and it reads well
  in diffs. `tomllib` keeps the core free of runtime dependencies (R1 of 001).
- **Alternatives**: CSV (too flat for stages and entrants), JSON (no comments), YAML (needs a
  dependency).

## R2. Ruleset model and validation

- **Decision**: frozen dataclasses (`Ruleset`, `StageRule`, `EntrantRule`, `KnockoutRule`,
  `CalendarRule`, `Tiebreaker` enum) built by a loader that validates the whole file first and
  returns every problem at once (same pattern as 001's import: `RulesetReport` with codes
  `R001…`). Each stage refers to earlier stages by id, and the loader checks the references, the
  counts (participants = groups × group size; places within range), the known criteria and the
  pairing feasibility.
- **Rationale**: FR-006 (report everything at once), and consistency with 001.
- **Alternatives**: a generic JSON-schema validator. It needs a dependency, and its errors are
  not domain-specific.

## R3. Stage types and the generic engine

- **Decision**: two stage types cover the Mineiro and the test ruleset.
  - **`groups`**:
    - `group_count` and `group_size`;
    - `matching`: `own_group`, `other_groups` or `all`;
    - `rounds`: 1 or 2;
    - a draw method (`pots_by_reputation` or `fixed`);
    - produces group tables plus an overall classification.
  - **`knockout`**:
    - `legs`: 1 or 2;
    - entrants from earlier results (`group_winners`, `best_of_place`, `overall_places`, `winners_of`);
    - `pairing`: `campaign_1v4_2v3` or `campaign_high_low`;
    - `deciding_leg_host`: `better_campaign`;
    - `tie_rule`: `penalties` or `points_then_campaign`;
    - `venue`: `home` or `neutral`.

  Side competitions (Troféu Inconfidência) are knockout stages tagged with a `track` that names
  the title they award. Outcomes (relegation) are declared as `overall_places` of a stage.
- **Rationale**: the Mineiro and most Estaduais are combinations of these pieces. Each new state
  format in v1 adds data first, and code only when a genuinely new stage type appears
  (Constitution VII: no speculative types).
- **Alternatives**: hard-coding the Mineiro in Python (rejected by the owner: each state has its
  own rules).

## R4. Seeds and determinism

- **Decision**:
  - `season_seed = int(sha256(f"{master_seed}:{year}")[:16], 16)`.
  - Every random decision gets its own sub-seed, derived the same way from a stable label: the
    draw (`"draw:{competition}"`), each match (`"match:{match_id}"`) and each final "draw lots"
    tiebreak (`"lots:{competition}:{sorted club ids}"`).
- **Rationale**:
  - Python's `hash()` is randomised per process, so it can't be used (Constitution II).
  - Per-decision sub-seeds make a match's result independent of the order the matches are
    simulated in, which is what later replays and partial re-simulation need.
- **Alternatives**: one shared RNG consumed in play order. It is fragile: any reordering changes
  every later result.

## R5. FMF-style seeded draw

- **Decision**: pots by reputation, with ties broken by club id. Pot 1 holds the top
  `group_count` clubs, pot 2 the next ones, and so on. Each pot is shuffled with the draw seed and
  dealt one club per group, in group order A, B, C.
- **Rationale**: it matches the press description (the big clubs head the groups) and stays
  deterministic.

## R6. Fixture generation for `other_groups`

- **Decision**: for 3 groups of 4, the "play the other groups" graph is the complete tripartite
  graph K4,4,4, which is 8-regular. It splits into 8 perfect matchings, one per matchday.
  - **Matchdays**: each matchday must pair every club exactly once with a club from another
    group. A naive split by group pairs (A–B, A–C, B–C) does not work, because with three groups
    one group would sit out. So matchdays are built by an exact perfect-matching search: each
    matchday is found by backtracking over clubs in id order, with candidate opponents ordered by
    the season seed, and pairs already used are removed. It is instant at 12 clubs and works for
    any `other_groups` setup whose match graph can be split into perfect matchings.
  - **Home/away**: assigned so that every club gets 4–4 (one alternating choice per K4,4 block,
    corrected by a balancing pass). Tests check the 4–4 balance on 1,000 seeds.
- **Rationale**: generic and deterministic, and the backtracking is tiny at this size.
- **Alternatives**: hand-written fixture tables for 12 clubs. Brittle, and per-format code.

## R7. Date generation (FR-011)

- **Decision**: the scheduler works on **rounds**: each matchday of a group stage, each knockout
  leg and each side-competition leg.
  - **Dependencies**: a round can be scheduled only after the round whose results it needs
    (pairings).
  - **Slots**: candidate slots inside the window are weekends (match days Saturday and Sunday)
    and midweeks (Wednesday and Thursday).
  - **Slot choice**:
    1. Count the rounds on the main path (Mineiro: 8 + 2 + 1 = 11).
    2. Use every weekend slot in the window, in order.
    3. If there are fewer weekend slots than main-path rounds, add the missing number of midweek
       slots, spread evenly through the group stage (where real calendars put them).
  - **Side rounds**: side-competition rounds share the slot of a main knockout round with the
    same position (Inconfidência semifinal legs go with the Mineiro semifinal legs). The
    Inconfidência final legs go on the main final's slot and on the next free slot.
  - **Days and times within a slot**: matches are spread over its days (e.g. 3 Saturday and
    3 Sunday). A club is placed on the later day of a weekend if it played midweek, so its rest
    stays at or above `min_rest_hours`.
  - **Kick-off times**: 16:00 on weekends and 21:30 midweek, from the ruleset defaults.
  - **Validation**: a validator checks every club's consecutive matches against the 66-hour
    minimum. It fails loudly if the window cannot fit (edge case).
- **Rationale**: it mirrors how Estadual tables are built (weekends first, midweek rounds to fit
  the CBF date cap) and it is deterministic and testable.
- **Alternatives**: a constraint solver. Overkill and a dependency.

## R8. Tiebreakers (FR-012)

- **Decision**: order a set of tied clubs by applying the ruleset's criteria in sequence.
  - **Criteria**:
    - `wins`, `goal_difference`, `goals_for`: plain comparisons;
    - `head_to_head`: applied only when **exactly two** clubs are still tied *and* they met; it
      compares points, then goal difference, in their mutual matches;
    - `fewer_red_cards`, `fewer_yellow_cards`: neutral when card data is missing (placeholder
      results);
    - `draw`: seeded lots.
  - **Order of application**: criteria apply to the whole tied subset. After each criterion, the
    subset splits into sub-groups and the remaining criteria apply inside each one.
  - **Audit**: each table row keeps a `decided_by` note (the criterion that separated it from the
    row below), so the owner can see why a club is above another.
- **Rationale**: this is the usual Brazilian regulation pattern. The per-criterion recursion
  handles three-way ties correctly, and the audit trail matches the owner's auditability
  preference.
- **Source**: customary order in CBF and Estadual regulations. Confirming it against the
  official FMF 2026 regulation is an open item (spec Assumptions).

## R9. Placeholder result simulator (FR-016)

- **Decision**: a `ResultProvider` protocol with
  `play(match, home: Club, away: Club, context) -> Result`. `PlaceholderProvider` implements it:
  - **Team strength**: the mean CA of the club's 11 best players, at least one of them a
    goalkeeper. This is cheap: the 001 best XI costs about 0.2 s per club, too slow for 1,000
    seasons, so it is not used.
  - **Goals**: Poisson with `λ_home = 1.30·e^{0.020·(S_h − S_a)}` and
    `λ_away = 1.05·e^{0.020·(S_a − S_h)}`, drawn from the match sub-seed.
  - **Penalties**: each kick scores with p = 0.75, then sudden death.
  - **Labelling**: every result carries `source = "placeholder"`, and the CLI prints a
    "resultado provisório" marker.
- **Rationale**: it is enough for plausible scorelines and for testing every rule path. It is
  deliberately not calibrated (spec 003 owns realism, Constitution I).

## R10. Season state and the facade

- **Decision**: `Season` is an in-memory engine object (mutable internally, deterministic). It is
  created by `start_season(dataset, ruleset_id, year, master_seed)`.
  - It holds the current date, matches, results, events and outcomes.
  - `advance_to(date)` plays day by day.
  - Read-only views (groups, fixtures, tables, bracket, calendar, outcomes) are immutable
    snapshots.

  The CLI has no saves until 004, so every CLI command rebuilds the season from
  (ruleset, year, master seed) and replays to `--date`. That is cheap (SC-005) and exact
  (Constitution II).
- **Rationale**: spec 004 will persist the same object, and the facade note from 001 (session
  handles) starts here.

## R11. Calendar and reserved windows (FR-019/020)

- **Decision**: `reference/calendar/brazil.toml` lists reserved windows as month-day ranges with
  labels and a `blocks` list (e.g. `["state"]` for FIFA dates), applied to any year.
  `SeasonCalendar(year)` exposes every date with its matches, events and windows. The Mineiro's
  window comes from its ruleset.
- **Placeholder windows**: the Copa do Brasil and the Brasileirão Série A–D are labelled from the
  published CBF calendar pattern, and the 2026 FIFA windows are used. All of this is
  approximate, to be refined when those competitions are specified.

## R12. Neutral venue

- **Decision**: the Mineiro ruleset declares
  `[venues.neutral] name = "Arena Estadual das Gerais", city = "Vale do Ouro", capacity = 62000`.
  It is fictional, a Mineirão equivalent in the sample world's capital. Real rulesets in
  `manager-data` can name the real stadium.
- **Rationale**: no change to the 001 data format, and the venue belongs to the competition rules.

## R13. CLI

- **Decision**: a new `season` command group (contracts/cli.md). Global options are `--ruleset`
  (default `mg-modulo-i-2026`), `--year` (default 2027, the sample world's reference year),
  `--master-seed` (default 20261002) and `--date` (default: end of season for results views,
  start of season for fixtures). All output is pt-BR via i18n.
