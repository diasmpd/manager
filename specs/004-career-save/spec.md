# Feature Specification: Career Save and Game Loop

**Feature Branch**: `004-career-save`

**Created**: 2026-10-03

**Status**: Draft

**Input**: Roadmap 004: "Career save (SQLite) and the day-by-day game loop". The owner's design
decisions were taken on 2026-10-03 as multiple-choice questions and are recorded under
[Owner decisions](#owner-decisions).

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's career
(save games, the "Continue" button that stops at events, season rollover, retirement and newgens).

## Owner decisions

Taken on 2026-10-03 as multiple-choice questions:
1. **Club**: the owner chooses any of the participating clubs when a career starts.
2. **"Continuar"**: it stops at events (FM style). Quiet days pass without stopping.
3. **Off-season**: after the Mineiro ends, the career skips to the next season. Players age a
   year. National competitions come in v1.
4. **Promotion**: relegated clubs are replaced by two generated clubs promoted from a
   Módulo II stand-in.
5. **Suspensions**: real rules. A red card means a one-match ban. Three yellow cards mean a
   one-match ban.
6. **Between seasons**: players age, and a simple development curve applies. The real
   training and development system is v1.
7. **Saves**: an autosave every in-game week, plus named saves. One SQLite file per save
   (Constitution).
8. **Retirement**: players decide when they retire (FM-like: likelier with age and declining
   ability, shaped by personality). Generated youngsters fill the squads.

## User Scenarios & Testing *(mandatory)*

The single user is the owner. Until the terminal game (spec 005), every scenario is exercised
through the core's command-line interface (Constitution III).

### User Story 1 - Start a career and save it (Priority: P1)

The owner starts a new career: they give it a name, choose a club and get a master seed. The
career is written to its own save file. The owner can list saves, load one and save under a new
name. Loading a save restores the career exactly: the same date, results, tables and squads.

**Why this priority**: everything else (the loop, seasons, suspensions) needs a career that
persists. It also makes the CLI stateful: until now every command rebuilt the season from the
seed.

**Independent Test**:
- Create a career and save it.
- Load it in a new process.
- Compare every view (date, table, fixtures, squads) with the original.

**Acceptance Scenarios**:

1. **Given** the sample world, **When** the owner starts a career with a name and a club, **Then** a
   save file is created and the career's current date is just before the first Mineiro match.
2. **Given** a saved career, **When** it is loaded, **Then** every view equals the view before saving.
3. **Given** a career, **When** the owner saves it under a new name, **Then** both saves exist
   independently and the list shows both.
4. **Given** a save written by a newer format version, **When** it is loaded, **Then** it is refused
   with a clear message (Constitution: schema changes ship with migrations).

---

### User Story 2 - Continue day by day (Priority: P2)

The owner presses "Continuar". The game advances day by day and stops at the next event that
concerns them:
- the user club's match day;
- a stage of the competition finishing (draw, qualification, title, relegation);
- the end of the season.

Quiet days pass without stopping. All other clubs' matches on those days are played by the
quick sim. Every in-game week the career is autosaved.

**Why this priority**: it is the core loop of the game. 005 puts a terminal UI on top of it.

**Independent Test**:
- From a new career, continue until the season ends.
- Count the stops.
- Check that every stop is an event, that no user match is skipped, and that autosaves
  happened weekly.

**Acceptance Scenarios**:

1. **Given** a new career, **When** the owner continues, **Then** the game stops on the user club's
   first match day, before kick-off. Continuing again plays that match.
2. **Given** days with no event, **When** the owner continues, **Then** they pass without stopping.
3. **Given** seven in-game days have passed since the last autosave, **When** the day ends, **Then**
   the autosave slot is written.
4. **Given** the same career and seed, **When** it is continued to the same date twice (or saved,
   loaded and continued), **Then** the results are identical (Constitution II).

---

### User Story 3 - Suspensions (Priority: P3)

Cards carry over between matches as in real competitions:
- a sent-off player misses the club's next match;
- a player who reaches three yellow cards misses the next match, and his count resets.

Suspended players are left out of the XI automatically. The owner sees who is suspended and
why.

**Why this priority**: cards already matter in tables (002). Suspensions make them matter for
squads, which is the first player-state rule of the career.

**Independent Test**:
- Play a season.
- For every red card and every third yellow, the player does not appear in the club's next
  match.
- He is available again afterwards.

**Acceptance Scenarios**:

1. **Given** a player sent off, **When** his club plays its next match, **Then** he is not in the
   squad, and he is eligible for the one after.
2. **Given** a player's third yellow card, **When** his club plays its next match, **Then** he is
   suspended, and his yellow count restarts at zero.
3. **Given** a suspended goalkeeper, **When** the team sheet is picked, **Then** the reserve keeper
   starts.
4. **Given** the end of the season, **When** the next season starts, **Then** cards and pending
   suspensions are cleared (state-championship practice). [Assumption: to confirm in the
   regulation.]

---

### User Story 4 - The next season (Priority: P4)

When the Mineiro ends, the career shows a season review, then moves to the next season:
- **Promotion and relegation:** the two relegated clubs leave, and two generated clubs are
  promoted from a Módulo II stand-in.
- **Players:** every player ages a year, and young players improve toward their potential
  while older ones decline.
- **Retirement:** some players decide to retire.
- **Squads:** generated youngsters fill each squad back to its size.

The new season is drawn and scheduled (002), and the owner continues as before.

**Why this priority**: it turns one season into a career. It depends on the loop and the save.

**Independent Test**: play five seasons. In every season:
- exactly 12 clubs take part;
- the relegated clubs from the previous season are absent and two new clubs are present;
- every squad is back to its size;
- players are a year older;
- retirements and development follow their curves.

**Acceptance Scenarios**:

1. **Given** a finished season, **When** the next one starts, **Then** its participants are the
   previous season's clubs minus the relegated ones, plus two promoted clubs.
2. **Given** a player aged 21 with potential above his current ability, **When** a season passes,
   **Then** his current ability tends to rise. **Given** a player aged 33, **Then** it tends to fall.
   Both are measured over many players.
3. **Given** a player aged 37, **When** the season ends, **Then** he is much likelier to retire than
   a player aged 30. A professional, ambitious player at his peak rarely retires.
4. **Given** retirements, **When** squads are refilled, **Then** each club has its squad size again,
   with generated youngsters (16–19).

### Edge Cases

- **A club with too few eligible players** (suspensions plus a small squad): the XI is
  completed as in 003 (short-squad flag), and the match is still played.
- **Suspended in the last match of the season:** the ban is cleared at season end (US3,
  scenario 4).
- **A two-legged tie:** a ban carries into the second leg. A red card in the first leg means
  the player misses the second.
- **A shootout:** cards in a shootout do not exist in the sim and do not count.
- **Autosave:** only one autosave slot. It is overwritten weekly and never replaces a named
  save.
- **Interrupted save:** a crash while saving must not corrupt the previous file. Writes are
  atomic: write a temporary file, then rename it.

## Requirements *(mandatory)*

### Functional Requirements

**Career and saves**

- **FR-001**: A career MUST record:
  - its name, master seed, user club and current date;
  - the world state (clubs, players and squads, as changed by seasons);
  - each season's competition state (002) with results (003 reports);
  - card counts and pending suspensions;
  - the history of finished seasons (outcomes, tables, top scorers).
- **FR-002**: A career MUST be saved to its own SQLite file in a saves folder. Each save MUST
  record:
  - the save format version;
  - the core and Python versions (Constitution II);
  - its creation and last-save timestamps (real-world time, for display only; never an input
    to the simulation).
- **FR-003**: Loading a save MUST reproduce the career exactly. A loaded career continued to
  any date MUST equal the original continued to that date.
- **FR-004**: The owner MUST be able to:
  - list saves;
  - save under a new name;
  - load a save;
  - delete a named save.

  An autosave slot is written every seven in-game days. It is separate from named saves and
  never overwrites them.
- **FR-005**: A save written by a newer format version MUST be refused with a clear message. An
  older version MUST be migrated forward, or refused when no migration exists.

**Game loop**

- **FR-006**: "Continuar" MUST advance day by day and stop at the first of:
  - the user club's match day, before kick-off;
  - a competition event (002 events: draw, qualified, paired, relegated, champion, title);
  - the end of the season.

  Days with no event pass without stopping.
- **FR-007**: All matches MUST be played by the quick sim (003), including the user club's,
  until the positional engine (007). In 005, the user's match will add choices before
  kick-off.

**Suspensions**

- **FR-008**: A red card (direct or second yellow) MUST suspend the player for his club's next
  official match.
- **FR-009**: A player's third yellow card in the competition MUST suspend him for his club's
  next match and reset his yellow count. A yellow cancelled by a second-yellow red counts
  toward the red only. This follows CBF practice. [Assumption: to confirm in the FMF
  regulation.]
- **FR-010**: Suspended players MUST be excluded when the team sheet is picked. Suspensions
  and cards MUST be cleared between seasons.

**Season rollover**

- **FR-011**: When a season ends, the career MUST:
  1. record the season's history;
  2. remove the relegated clubs from the next season's participants;
  3. generate two promoted clubs (fictional, with full squads, at Módulo II strength);
  4. age and develop players;
  5. apply retirements;
  6. refill squads with generated youngsters;
  7. start the next season (002 draw and schedule) on a seed derived from the career's master
     seed and the year.
- **FR-012**: Development MUST move current ability toward potential for young players and
  away from it for older ones. It uses a placeholder age curve with seeded noise, and it acts
  on attributes so that CA stays derived (001). The curve MUST be data, not code. The real
  training system is v1.
- **FR-013**: Retirement MUST be the player's own decision: a seeded probability rising with
  age, raised by declining ability and lowered by professionalism and ambition (FM's
  hidden-attribute logic). It is data-driven like FR-012. No player under 30 retires in M0.
- **FR-014**: Generated youngsters MUST be created by the 001 sample generator's player
  model, aged 16–19, with potential above current ability. Each club MUST end the rollover
  with its squad size restored.

**Viewing (CLI)**

- **FR-015**: The CLI MUST offer:
  - `career new`, `career list`, `career load`, `career save --as`, `career delete`;
  - `career continue` (to the next stop), `career status` (date, next match, suspensions);
  - `career history`.

  The existing `season` views MUST work on the loaded career instead of rebuilding from a
  seed. All output is in pt-BR.

### Key Entities

- **Career**: name, master seed, user club, current date, world (dataset, possibly changed by
  rollovers), current season (002 `Season` state), discipline state, history.
- **Save**: one SQLite file. It holds the format version, the core and Python versions and the
  timestamps, and serialises the career's state.
- **Discipline**: per player in the current season, a yellow count and the matches still to
  serve.
- **Season history**: year, champion, side titles, relegated and promoted clubs, final table,
  top scorers.
- **Stop**: why the loop stopped (user match, event, season end) and the date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A career saved and loaded at any of 50 random stopping points continues
  identically to one never saved (bit for bit on results).
- **SC-002**: Continuing from a new career to the end of a season takes under 5 seconds,
  including weekly autosaves. One "Continuar" between two user matches takes under 1 second
  (Constitution: a day without matches in ≤ 1 s).
- **SC-003**: Over 100 simulated seasons, 100% of red cards and third yellows produce exactly
  one missed match by the player in his club's next match, and no suspended player appears
  in a match.
- **SC-004**: Over a 10-season career, the league always has 12 clubs, and every squad is
  restored to its size at each rollover. The age distribution stays stable: mean squad age
  within 24–28 in every season.
- **SC-005**: Retirement ages over 10 seasons have a median of 34–36 (typical for professional
  footballers). No player under 30 retires.
- **SC-006**: An interrupted save never leaves a corrupt file. A save killed mid-write leaves
  the previous version loadable (tested by simulating a failure between the write and the
  rename).

## Assumptions

- **Squad size:** the sample world's 27 players per club. Promoted clubs get the same.
- **Promoted-club strength:** "Módulo II strength" means generated at the lower reputation
  and ability band of the sample generator. The exact band is set in the plan.
- **Development and retirement curves** are placeholders, fitted only so that SC-004 and
  SC-005 hold. They will be replaced by the v1 development system, calibrated against real
  ageing curves (Constitution I).
- **Clearing cards at season end** and the three-yellow threshold follow common Brazilian
  state-championship rules, to be confirmed in the FMF regulation (consistent with the owner's
  choice to keep the press-based ruleset for now).
- **Single user club**: there is no job market or sacking in M0 (finances and board are v1).
- **The user's club being relegated** is out of scope for M0 (owner, 2026-10-03: this is a basic
  test version). No special handling is specified.
- **The saves folder** defaults to `saves/` next to the data folder, configurable with `--saves`.
  Saves are personal data and are git-ignored.
