# Feature Specification: 2D Match View

**Feature Branch**: `008b-match-view`
**Created**: 2026-10-13
**Status**: Draft
**Input**: Roadmap item 008b: "2D match view in the Godot window, replaying 008's positional
record (owner decision, 2026-10-05)".

## Context

Spec 008 gave the user's matches a positional engine and kept the match view as text. The engine
already writes a positional record for each of the user's matches: the ball and all 22 players,
twice a second, with the match events tied to their samples. This spec draws that record as a
top-down pitch in the desktop window, during the match and afterwards.

Football Manager is the benchmark. FM's 2D classic view shows the pitch from above with a disc
for each player in his club's colours and shirt number, the ball, a scoreboard and the commentary
line; the manager picks a speed, can pause at any time to change things, and can watch a finished
match again. This spec follows that. Where it does less than FM, the Assumptions say so.

Decisions taken for the owner (he follows the recommendation; each can be reversed at review):

1. **The view is live, not only a replay.** The pitch moves while the match is played, next to
   the feed, because watching the match is the point. A finished match can also be watched again.
2. **The whole match is shown.** FM's "key highlights" modes are left out of this spec: there is
   no model yet of which passages matter, and speed control covers the need.
3. **The text view stays.** The owner can switch between pitch and text at any time; the feed and
   the stats are the same in both.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Watch my match on the pitch (Priority: P1)

The owner starts his match. The window shows the pitch from above: his eleven and the opponent's
as discs in each club's colours with shirt numbers, and the ball. The discs move as the match is
played. The scoreboard shows the clock and the score, and the feed line shows what just happened.
He picks how fast the match runs.

**Why this priority**: it is the feature. Everything else builds on a pitch that shows the match.

**Independent Test**: start a user match in the client and let it run to full time on the pitch
view. The positions on screen match the positional record sample for sample, and the final score
on the scoreboard matches the match report.

**Acceptance Scenarios**:

1. **Given** the owner's match is pending, **When** he starts it, **Then** the pitch shows both
   teams in their kick-off positions, in their clubs' colours, with shirt numbers, and the ball
   on the centre spot.
2. **Given** the match is running, **When** time passes, **Then** every disc and the ball move
   smoothly between the recorded positions, and the clock and score follow the match.
3. **Given** the match is running, **When** a goal, a card, a substitution or a penalty happens,
   **Then** the pitch shows it at the moment it happens (the scorer and the ball in the goal, the
   booked player marked, the players swapped), and the feed shows the same line as the text view.
4. **Given** the match is running, **When** the owner changes the speed, **Then** the match runs
   at the new speed from that moment and the positions stay in step with the clock.
5. **Given** both clubs wear similar colours, **When** the match starts, **Then** the away side
   is drawn in its alternative colours so the two sides can be told apart.
6. **Given** a high ball (a cross, a long pass, a goal kick), **When** it is in the air, **Then**
   the ball is drawn so that its height can be read (larger, with a shadow on the ground).

---

### User Story 2 - Pause and change things from the pitch (Priority: P2)

The owner pauses at any moment. The pitch freezes. He makes a substitution or changes his tactic,
exactly as in the text view, and resumes. The pitch shows the change from that moment.

**Why this priority**: pausing at any time and acting is an 008 owner decision. The pitch view
must not lose it, or the owner has to leave the view to manage.

**Independent Test**: pause on the pitch view, make a substitution and a tactic change, resume.
The decisions are recorded with the pause time, and replaying the match from its seed and those
decisions gives the same record as the one that was watched.

**Acceptance Scenarios**:

1. **Given** the match is running, **When** the owner pauses, **Then** nothing on the pitch moves
   and the clock stops, until he resumes.
2. **Given** the match is paused, **When** he substitutes a player, **Then** on resuming the new
   player's disc is on the pitch with his number, and the one who left is gone.
3. **Given** the match is paused, **When** he changes formation or instructions, **Then** on
   resuming the players move to the new shape as the engine plays it.
4. **Given** a player is sent off or injured, **When** play resumes, **Then** his disc is gone,
   and the pitch shows the side with one fewer.
5. **Given** the owner selects a disc, **When** he looks at it, **Then** he sees the player's
   name, position, energy and whether he is booked (the same facts as the text view's list).

---

### User Story 3 - Watch a finished match again (Priority: P3)

After the match, or later from the calendar, the owner opens one of his played matches and
watches it on the pitch. He can pause, change speed, drag along a timeline, and jump straight to
a goal, a card or a penalty.

**Why this priority**: it is what the positional record was stored for, and the way to look at a
goal again. It needs the pitch of story 1 and nothing from story 2.

**Independent Test**: play a match, save, close and reopen the career, open the match from the
calendar and jump to each goal. Each jump shows the moments before the goal and the goal itself,
and the score on the scoreboard is the score at that moment.

**Acceptance Scenarios**:

1. **Given** a played user match with a record, **When** the owner opens its replay, **Then** the
   pitch shows the match from kick-off with a timeline of its events.
2. **Given** a replay, **When** he picks a goal on the timeline, **Then** the replay starts a few
   seconds before the goal.
3. **Given** a replay, **When** he drags the timeline, **Then** the pitch, the clock and the
   score show that moment.
4. **Given** a replay, **When** it runs, **Then** no substitution or tactic control is offered:
   a finished match cannot be changed.
5. **Given** a match without a record (a background match, or a save from before 008), **When**
   the owner looks at it, **Then** no replay is offered, and the report is shown as today.

---

### Edge Cases

- A player's sample is "not on the pitch" (before he comes on, after he goes off or is sent off):
  no disc is drawn, and no disc slides in from a corner of the pitch.
- A substitution between two samples: the outgoing disc disappears and the incoming one appears
  at its own first position, without one disc sliding across the pitch into the other.
- Half-time: the sides change ends if the record has them change ends. The view draws what the
  record says and never mirrors positions itself.
- A dead ball (throw-in, corner, free kick, goal kick, kick-off after a goal): the discs walk to
  their places as recorded; the view does not skip or teleport.
- The window is resized or is narrow: the pitch keeps its 105 × 68 proportions, and the
  scoreboard, feed and controls stay readable.
- The fastest speed on a slow PC: the view may drop frames, but the clock, the score and the
  final result are never affected by how fast the screen draws.
- A penalty shootout, when a competition has one: the view shows the kicks if the record has
  them, and otherwise shows the shootout as text.
- The owner switches to the text view and back in mid-match: the pitch resumes at the current
  moment, not where he left it.
- A replay is opened for a match of an earlier season: it plays from the stored record, with the
  clubs' colours and the players' names as they were stored for that match.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The desktop client MUST show the user's live match on a top-down 2D pitch with
  standard markings, in the proportions of the engine's pitch (105 × 68 m).
- **FR-002**: Each player on the pitch MUST be drawn as a disc in his club's colours with his
  shirt number. Goalkeepers MUST be distinguishable from outfield players of both sides.
- **FR-003**: When the two clubs' colours are too alike to tell apart, the away side MUST be drawn
  in alternative colours. The rule for "too alike" MUST be deterministic.
- **FR-004**: The ball MUST be drawn at its recorded position, and its height MUST be readable.
- **FR-005**: Positions on screen MUST come only from the positional record. The client MUST NOT
  compute, predict or correct football: between two samples it may only interpolate
  (Constitution III).
- **FR-006**: The view MUST show the clock, the score, both clubs' names and the latest feed
  line, and MUST keep the stats and the full feed one action away.
- **FR-007**: The view MUST mark, at the moment they happen: goals, yellow and red cards,
  substitutions, penalties and injuries.
- **FR-008**: The owner MUST be able to pause and resume at any time and to choose the speed from
  a fixed set that includes real time and faster speeds.
- **FR-009**: While the match is paused, the owner MUST be able to make substitutions and tactic
  changes from the pitch view, with the same rules, errors and messages as the text view.
- **FR-010**: Selecting a disc MUST show that player's name, position, energy and cards.
- **FR-011**: The owner MUST be able to switch between the pitch view and the text view during
  the match without affecting it, and the client MUST remember his last choice.
- **FR-012**: The core MUST give the client the positional samples of the part of the match just
  played, in the same form as the stored record, through the versioned local API. The engine MUST
  NOT change for this (Constitution III).
- **FR-013**: Watching, pausing, changing speed or switching views MUST NOT change the match: the
  same seed and decisions MUST give the same events, result and record as with the text view or
  with no view at all (Constitution II).
- **FR-014**: The owner MUST be able to open the replay of any of his played matches that has a
  record: right after the match, and later from where the played match is listed.
- **FR-015**: A replay MUST offer pause, the speed set, a timeline that can be dragged, and a
  jump to each goal, card and penalty. It MUST offer no way to change the match.
- **FR-016**: A match without a record MUST offer no replay, with no error.
- **FR-017**: All text in the view MUST be PT-BR, and the view MUST follow the client's
  scoreboard look in the user club's colours.
- **FR-018**: The view's logic that can be checked without a screen (sample to screen position,
  interpolation, appearing and disappearing discs, the colour clash rule, the event timeline)
  MUST have automated tests (Constitution IV).

### Key Entities

- **Positional record** (exists, spec 008): the sampled positions of the ball and 22 players of
  one user match, the players and their sides in sample order, and the match events tied to
  their samples. This spec reads it and does not change its stored form.
- **Record chunk**: the samples and events of the part of a live match just played, in the
  record's form, so that a live match and a replay are drawn by the same code.
- **Kit colours**: for each club, the colours its discs are drawn in, and the alternative used
  on a clash. For a replay, the colours of the match as it was played.
- **Playback state**: the moment being shown, the speed, and paused or running. It belongs to
  the client and is never part of the match.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can watch a full match of his club on the pitch from kick-off to full
  time without opening the text view, and still knows the score, the scorers and the cards.
- **SC-002**: For every sample of a played match, each disc and the ball are drawn at the
  recorded position, to within the width of one disc.
- **SC-003**: Movement looks continuous at every speed: at real time on the reference PC, the
  pitch is redrawn at least 30 times a second.
- **SC-004**: A match watched on the pitch view, with pauses and speed changes, gives a record
  identical to the same match played with the text view and the same decisions.
- **SC-005**: From a played match in the calendar, the owner reaches any goal of that match in
  at most three actions, and the replay starts within 2 seconds.
- **SC-006**: A substitution or a tactic change made from the pitch view takes no more actions
  than the same change from the text view.
- **SC-007**: Starting the pitch view adds at most 1 second to starting a match, and playing a
  match at the fastest speed takes at most 10% longer than with the text view.

## Assumptions

- **Top-down 2D only.** No 3D, no camera angles, no zoom, no player animation: discs and a ball.
  3D stays on the roadmap's later path, reading the same record.
- **The whole match is played out.** FM's highlight modes (key, extended, comprehensive) are not
  in this spec; the speed set and, in a replay, the jump to events cover it.
- **The record is used as 008 stores it**: two samples a second, positions only. The view shows
  no pass lines, runs or player facing, and does not ask the engine for more data. If two samples
  a second prove too coarse to look right, that is a later change to the record, not to this
  spec.
- **Only the user's matches have a pitch view.** Background matches have no record (008).
- **Kit colours** come from the club colours the client already uses. If the dataset has no
  alternative colours, a fixed neutral kit is the alternative.
- **Shirt numbers**: if the dataset has none, numbers come from the team sheet in a stable order.
- **No sound** and no crowd.
- **No assistant advice on the pitch view** (010) and no ratings or xG overlays (009).
- **One match at a time.** Other matches of the match day are shown as today.
- **Replays are not exported** as video or files.
- **Not a calibration target.** The view adds no simulation system, so it has no calibration
  harness of its own (Constitution I); it must only leave the positional gates unchanged
  (FR-013).
- Depends on 007 (the desktop client and the local API) and 008 (the positional record and the
  live-match methods). It is built on the 008 branch until 008 is merged.
