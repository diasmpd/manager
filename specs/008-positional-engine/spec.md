# Feature Specification: Positional Match Engine

**Feature Branch**: `008-positional-engine`

**Created**: 2026-10-05

**Status**: Draft

**Input**: Roadmap 008, "Positional match engine: continuous movement, smart player behaviours
(card caution, energy management, game state), cross-validated with 003". The owner's decisions
were taken on 2026-10-05 as multiple-choice questions.

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's match engine.
In FM, 22 players and the ball move on a pitch. Each player decides from his attributes, his roles
and instructions, and the tactic. The highlights the manager sees are the key moments of that
simulation.

## Owner decisions (2026-10-05)

1. **The match view stays text in 008.** The live feed and the stats stay as they are. The engine
   records every player's and the ball's position over time, so that a 2D pitch view in the
   desktop window can replay matches. That view is its own spec, right after this one.
2. **Pause at any time, FM-style.** During his matches the owner can pause whenever he wants. While
   paused he can make substitutions and change:
   - the mentality;
   - the team and player instructions;
   - the roles;
   - the in- and out-of-possession formations.

   The changes act from that moment.
3. **The quick sim's goal spread is fixed within 008.** The quick sim has too few 3-goal matches
   (20.44%, real 24.5%), and the milestone gate fails by 0.06 points. The positional engine's game
   state is where the realistic mechanism is found. It is carried back to the quick sim, and both
   gates pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - My matches are played on a pitch (Priority: P1)

When the owner's club plays, the match is simulated with 22 players and the ball moving on a
pitch. Players act from their attributes, the tactic, their roles and instructions. The owner
follows the live feed as today. Its moments (chances, saves, fouls, cards, goals, substitutions)
come from what actually happened on the pitch, and so do the stats at full time.
- Background matches (other clubs) stay on the quick sim.
- Tables, suspensions and the rest of the career work exactly as before.

**Why this priority**: it is the roadmap item, and the base for 2D and 3D.

**Independent Test**: play a career to the first user match. That match is played by the new
engine, and its feed and stats come from the positional simulation. The other matches of the day
come from the quick sim. Replaying the match from its seed gives the same match.

**Acceptance Scenarios**:

1. **Given** a user match day, **When** it is played, **Then** the user's match is simulated
   positionally and the others by the quick sim.
2. **Given** a played user match, **When** it is replayed from its seed and the recorded
   decisions, **Then** the result, the events and the positions are identical.
3. **Given** a played user match, **When** its record is read, **Then** it contains every
   player's and the ball's positions over the whole match, sampled at least twice per second.
   That is enough for a 2D replay.

---

### User Story 2 - Realistic numbers (Priority: P1)

The positional engine's matches look like real Brazilian football, by the same measures as the
quick sim:
- goals per match, the home, draw and away split, and the spread of total goals;
- shots, shots on target, xG, corners, fouls and cards;
- when goals happen (by period, late goals);
- favourites against underdogs.

**Why this priority**: realism is the project's first principle (Constitution I). A positional
engine that only looks good is not enough.

**Independent Test**: run the calibration harness on the positional engine (PR sample and
milestone sample). Every primary target is inside its band. A cross-validation run (the same
fixtures through both engines) shows matching distributions.

**Acceptance Scenarios**:

1. **Given** the PR and milestone samples, **When** they are played by the positional engine,
   **Then** every primary target is inside its band.
2. **Given** the same fixtures, **When** they are played by both engines, **Then** goals, results,
   shots, cards and the spread of totals agree within the cross-validation tolerances.
3. **Given** the 3-goal shortfall, **When** the mechanism found in the positional engine is
   carried to the quick sim, **Then** both of the quick sim's gates pass.

---

### User Story 3 - Pause and manage during the match (Priority: P2)

During his match the owner can pause at any moment. While paused he can:
- make substitutions (within the rules: the number of changes and windows);
- change the mentality, the team and player instructions, the roles, and the formations
  (formations within the selection's players).

On resume, the match continues with the changes from that minute. The feed notes them.

**Why this priority**: in-match management is a large part of FM and the owner's choice. It comes
after the engine itself.

**Independent Test**:
- pause at minute 60, make a substitution and switch to an attacking mentality, then resume;
- the substitute plays from minute 60, and the team takes more shots than in the same match
  replayed without the change;
- replaying the match with the recorded decisions reproduces it exactly.

**Acceptance Scenarios**:

1. **Given** a match in progress, **When** the owner pauses, **Then** the simulation stops at that
   moment and shows the score, the minute and the stats so far.
2. **Given** a pause, **When** the owner substitutes a player, **Then** the substitute is on the
   pitch from that minute. Substitutions beyond the rules are refused, with the reason.
3. **Given** a pause, **When** the owner changes the tactic, **Then** the team plays with it from
   that minute, and the change is recorded with its minute.
4. **Given** a sent-off player, **When** the owner tries to substitute him, **Then** it is refused,
   as in real football.

---

### User Story 4 - Players behave like players (Priority: P2)

The behaviours the quick sim models statistically come from player decisions:
- **Card caution**: a booked player holds back in challenges, depending on his temperament and
  decisions (spec 003).
- **Energy**: players tire with distance run and intensity. Tired players are slower and make
  worse decisions, and the assistant's substitutions respond to fatigue.
- **Game state**: a trailing side pushes forward and exposes itself, and a leading side protects
  its lead.
- **Tactics**: the 006 options act through positions and decisions, not only through levers. A
  high line holds a high position, pressing chases the ball, and width spreads the team.

**Why this priority**: these are the owner's "smart behaviour" items from the roadmap. They are
what makes a positional engine worth having.

**Independent Test**: paired-seed statistical tests, one per behaviour:
- a booked defender commits fewer fouls;
- the average distance run per player is in a realistic range, and tired players lose more duels;
- late trailing sides take more shots;
- a high defensive line plays measurably higher up the pitch.

**Acceptance Scenarios**:

1. **Given** a booked player, **When** compared with the same player unbooked, **Then** he commits
   fewer fouls.
2. **Given** a full match, **When** distances are measured, **Then** outfield players cover a
   realistic distance, and their sprint share falls late in the match.
3. **Given** a team trailing late, **When** compared with level, **Then** it takes more shots and
   concedes better chances.
4. **Given** two tactics that differ in one option (e.g. defensive line), **When** played on paired
   seeds, **Then** the documented positional effect is visible (e.g. the average line height).

---

### User Story 5 - Both windows can pause (Priority: P3)

The Godot window and the terminal UI both show the live feed and offer pause, substitution and
tactic changes. They go through the core's contract, so no rule lives in a client.

**Why this priority**: the owner plays in the Godot window. The terminal stays a supported client.

**Independent Test**: in both clients' automated tests, pause a match, make a substitution and
resume. The match continues with the substitute.

**Acceptance Scenarios**:

1. **Given** a live user match in the Godot window, **When** the owner presses pause, **Then**
   the substitution and tactic screens open for the match in progress.
2. **Given** the same in the terminal UI, **When** the owner pauses, **Then** the same actions are
   available.

### Edge Cases

- **Closing the window during a match**: the match state is not lost. Either the match finishes
  in the background before saving, or the career resumes before that match day, never in the
  middle. The plan picks one and documents it.
- **A red card while paused**: impossible; events only happen while the match runs.
- **All substitutions used, then an injury-like situation**: the team plays on with fewer
  players. Injuries are not in M0.
- **A goalkeeper sent off with no keeper on the bench**: an outfield player goes in goal, as in
  the quick sim.
- **Extra time and penalties** in knockout ties: played by the engine (extra time) and by the
  existing shootout model (penalties).
- **A very long pause**: no time limit.
- **An old save from before 008**: played and replayed matches stay valid. Past matches are
  never re-simulated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The user club's matches MUST be simulated by the positional engine. Every other
  match MUST stay on the quick sim.
- **FR-002**: Players and the ball MUST move continuously on a pitch of real dimensions. Each
  player MUST act from his attributes, the tactic (formations, mentality, instructions), his
  roles and player instructions, and the match state.
- **FR-003**: The engine MUST produce the same report as the quick sim: events with minutes,
  players and xG; stats; line-ups; finishers. Feeds, news, suspensions and tables MUST keep
  working unchanged.
- **FR-004**: The engine MUST record the positions of all players and the ball, sampled at least
  2 times per second, as a positional record that a 2D or 3D view can replay without the engine
  (Constitution III).
- **FR-005**: A match MUST be fully reproducible from its seed and the recorded user decisions:
  the same events, the same result, the same record (Constitution II).
- **FR-006**: The owner MUST be able to pause his match at any time and, while paused:
  - make substitutions (the real limits on numbers and windows apply; sent-off players cannot be
    replaced);
  - change the mentality, the team and player instructions, the roles, and the formations.

  Changes MUST act from the pause minute, and MUST be recorded with that minute.
- **FR-007**: These behaviours MUST emerge from player decisions:
  - card caution, by temperament and decisions;
  - energy and fatigue, with the assistant's substitutions;
  - game state: chasing, protecting, and a level game opening up;
  - every 006 tactical option's positional meaning.
- **FR-008**: The positional engine MUST pass the same calibration targets, PR and milestone
  gates, as the quick sim, through the same harness.
- **FR-009**: A cross-validation check MUST play the same fixtures through both engines and
  compare the distributions within stated tolerances.
- **FR-010**: The quick sim's 3-goal shortfall MUST be fixed by a mechanism grounded in the
  positional engine's game-state behaviour, so that both of the quick sim's gates pass. The
  targets MUST stay unchanged.
- **FR-011**: A positional match MUST simulate in at most 10 s headless on the reference PC
  (Constitution). A user match day MUST NOT take noticeably longer than that in the windows.
- **FR-012**: The Godot window and the terminal UI MUST both offer pause, substitution and tactic
  changes, through the local API contract (a new minor contract version). No client may contain
  the rules.
- **FR-013**: Shootouts after a drawn knockout tie MUST use the existing player-based shootout
  model. Extra time, where the rules call for it, MUST be played by the engine.

### Key Entities

- **Positional record**: the match's sampled positions (players and the ball) over time, with
  the event markers. It is stored with the match and replayable on its own.
- **Match decision**: a user action during a match (substitution or tactic change), with the
  minute and second. Together with the seed, it reproduces the match.
- **Live match**: a match being played that can be paused and resumed. It holds the current
  state (score, minute, players on the pitch, energy, the tactic).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every primary calibration target passes on the positional engine, in both the PR
  sample and the milestone sample.
- **SC-002**: Both quick-sim gates pass, the milestone 3-goal floor included, with unchanged
  targets.
- **SC-003**: Cross-validation: on the same fixtures, both engines' goals per match agree within
  0.15, the home, draw and away shares within 4 points, and each total-goals share within 4
  points.
- **SC-004**: A positional match takes at most 10 s headless on the reference PC. A full season
  with the user's matches positional takes at most 2 minutes.
- **SC-005**: A user match replayed from its seed and decisions is identical, in 100% of test
  cases.
- **SC-006**: Each behaviour in FR-007 has a paired-seed test showing its direction.
- **SC-007**: A pause, a substitution and a tactic change, then resume, works in both the Godot
  window and the terminal UI (automated tests).

## Assumptions

- **Background matches stay on the quick sim** (Constitution: two-tier).
- **Injuries and weather are not in M0**; they come with later specs.
- **The match view stays text.** The 2D pitch view is the next spec, and it replays the
  positional record.
- **Positions are recorded for the user's matches only.** Background matches have no positional
  record.
- **The live feed's wording** stays as in 005. Richer commentary comes with the match report spec.
- **Substitution rules** follow the competition's ruleset: five substitutions in three windows
  plus half-time, as in the quick sim (spec 003).
- **The 3-goal mechanism** found in the positional engine is described in plain terms, and the
  quick sim's version is a statistical counterpart of it, calibrated with the quick-sim tuner.
