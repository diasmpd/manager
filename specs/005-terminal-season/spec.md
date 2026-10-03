# Feature Specification: Playable Season in the Terminal

**Feature Branch**: `005-terminal-season`

**Created**: 2026-10-03

**Status**: Draft

**Input**: Roadmap 005: "Playable Mineiro season from the terminal (Python TUI): includes basic
squad and lineup selection (and formation choice), so the user makes real decisions before 006".
The owner's design decisions were taken on 2026-10-03 as multiple-choice questions.

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's main screens
(left-hand menu, squad, team selection, match day, competition tables, calendar, inbox).

## Owner decisions

1. **Interface**: a full-screen terminal UI, with keyboard navigation and FM-like panels.
2. **Team selection**: the assistant proposes the XI and bench, and the owner edits them (swaps
   players, chooses the formation) before confirming.
3. **Match day**: a live text feed of the key moments, then the full report.
4. **Screens**: squad with player profiles, tables and fixtures, and calendar with news, plus
   team selection and match day. A saves screen is not included: saves stay in the CLI (004).
   The game autosaves weekly and saves on quit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Play a season from the terminal (Priority: P1)

The owner opens the game with an existing career (or creates one from the CLI) and sees a home
screen:
- the date;
- the next match;
- the club's table position;
- the latest news.

From a left-hand menu he moves between screens and presses "Continuar" to advance. Before each
of his matches the game stops on team selection. After confirming, the match is played with a
live feed. The season goes on to its end, and then into the next season.

**Why this priority**: it is Milestone 0's goal: a season you can play.

**Independent Test**: with a scripted key sequence (the UI's test pilot), create a career,
continue to the first match, confirm the proposed XI, watch the feed to full time and continue
to the season end. No screen crashes, and the career's results equal those of the same career
continued from the CLI.

**Acceptance Scenarios**:

1. **Given** a career, **When** the game opens, **Then** the home screen shows the date, the next
   match, the table position and the latest news.
2. **Given** the home screen, **When** the owner presses Continuar, **Then** the game advances to the
   next stop (004) and shows it: the user match day opens team selection, and events go to the
   news.
3. **Given** a finished season, **When** the owner continues, **Then** the season review is shown,
   then the next season starts.
4. **Given** the game is closed, **When** it is reopened, **Then** the career resumes where it was
   (saved on quit).

---

### User Story 2 - Pick the team (Priority: P2)

Before each of his matches, the owner sees the assistant's proposed XI in a formation, with the
bench and the rest of the squad:
- suspended players are greyed out and cannot be picked;
- each player shows his position and how well he fits the slot;
- the owner can change the formation (the five available ones) and swap any two players.

The assistant can re-pick the best XI at any time. On confirm, the match uses exactly that
selection.

**Why this priority**: it is the first real decision the owner makes. It turns watching into
managing.

**Independent Test**:
- Swap a starter with a bench player and change the formation.
- Confirm, and check that the match report's lineup equals the selection.
- A suspended player can never be selected.

**Acceptance Scenarios**:

1. **Given** a user match day, **When** team selection opens, **Then** the proposal equals the
   assistant's best XI for the club's last formation (default 4-4-2), without suspended
   players.
2. **Given** the owner swaps two players or changes the formation, **When** he confirms, **Then** the
   report's starting XI and bench are exactly his selection.
3. **Given** a suspended player, **When** the owner tries to select him, **Then** it is refused with
   the reason.
4. **Given** a selection without a goalkeeper in goal, **When** the owner confirms, **Then** he is
   warned and can confirm anyway (FM lets you).

---

### User Story 3 - Match day feed (Priority: P3)

The match plays as a feed of key moments with the minute and the score:
- chances and shots on target;
- goals with scorer and assister;
- cards;
- substitutions;
- half-time and full-time.

Speed is adjustable (slow, normal, fast, instant). At full time the full report (003) is shown.

**Why this priority**: it is how the owner experiences his matches until the 2D view.

**Independent Test**: the feed shows every goal, card and substitution of the report, in order,
with the score correct at each line. At "instant" speed it goes straight to the report.

**Acceptance Scenarios**:

1. **Given** a played match, **When** the feed runs, **Then** every report event appears once, in
   minute order, and the running score matches.
2. **Given** a speed change, **When** the feed runs, **Then** the pace changes and the content does
   not.

---

### User Story 4 - Squad, tables, fixtures, calendar and news (Priority: P4)

These screens show:
- **Squad**: the club's players with position, age, ability as stars (relative to the squad,
  FM-like: CA is never shown as a number), status (suspended, number of yellow cards) and
  season stats (appearances, goals, assists, cards). Opening a player shows his FM-style
  profile (001).
- **Tables and fixtures**: group tables, the overall classification with zones, the bracket,
  the club's fixtures and results, and any match report.
- **Calendar**: the month view (002) with the club's matches highlighted.
- **News**: an inbox of dated items: the draw, the club's results, suspensions, stage
  qualifications, titles, relegations and the season review.

**Why this priority**: they make the season readable. They come last because US1–US3 already
make it playable.

**Independent Test**: each screen opens without error at three points of a season (start,
middle, end) and shows the same data as the matching CLI view.

**Acceptance Scenarios**:

1. **Given** the squad screen, **When** a player is opened, **Then** his profile shows the visible
   attributes (hidden ones only with the debug flag, as in 001).
2. **Given** a suspension, **When** the news is opened, **Then** an item names the player and the
   number of matches.

### Edge Cases

- **A terminal too small:** the UI shows a "resize" message instead of a broken layout
  (minimum 100×30).
- **Quitting during selection or a feed:** the match is not played. On reopening, the game is
  back before the match. A feed already started has a fixed result (it was simulated at
  confirm), so reopening shows the report.
- **A selection that became invalid** (a player suspended after it was saved): it is re-proposed
  and the owner is told.
- **Windows Terminal and the classic console:** both are supported. Colours degrade gracefully.

## Requirements *(mandatory)*

### Functional Requirements

**Architecture**

- **FR-001**: The terminal UI MUST hold no game rules (Constitution III). It calls only the core
  facade. Any rule it needs (e.g. who can be selected) is a facade function.
- **FR-002**: The UI MUST be a separate package with its own dependency (Textual). The core stays
  free of runtime dependencies.

**Selection (core)**

- **FR-003**: The career MUST hold the user's selection (formation, XI by slot, bench), and the
  user's matches MUST be played with it. Other clubs keep the assistant's sheets (003).
- **FR-004**: The facade MUST offer:
  - the assistant's proposal for a formation;
  - validation of a selection, with reasons: suspended, not in the squad, duplicated, bench
    too long, no goalkeeper (a warning only);
  - confirming the selection.

  The selection is saved with the career (save format v2, with a migration from v1).
- **FR-005**: Results MUST stay deterministic. The same career, selection and seed give the same
  match.

**Screens**

- **FR-006**: Home, Squad (with profile), Team selection, Match day, Tables/Fixtures, Calendar and
  News, with a left-hand menu and keyboard shortcuts. Every text is in pt-BR, through the i18n
  layer.
- **FR-007**: Continuar MUST behave exactly as 004's `career continue`. A user match stop opens
  team selection.
- **FR-008**: The feed MUST replay the match report's events in order at the chosen speed. The
  match is simulated in full when the selection is confirmed. The feed is presentation only.
- **FR-009**: News items MUST be derived from the career (season events, results, suspensions,
  history) by a facade function, not stored separately.
- **FR-010**: The game MUST save on quit and keep 004's weekly autosave.

**Launch**

- **FR-011**: `python -m manager_tui [--saves DIR] [CAREER]` MUST open the given career, or the
  most recently saved one. With no saves, it MUST explain how to create one (`career new`).

### Key Entities

- **Selection**: formation, starters (slot → player), bench (ordered), and the date it was set.
- **NewsItem**: date, kind, text key and parameters, and a related club, player or match.
- **FeedLine**: minute, text and the score after the line.

## Success Criteria *(mandatory)*

- **SC-001**: A scripted session (the test pilot) can play a full season from new career to
  season review without errors, in under 60 seconds at instant speed.
- **SC-002**: For 20 random matches, the report's lineup equals the confirmed selection.
- **SC-003**: Every screen renders at the minimum size (100×30), with snapshot tests for each.
- **SC-004**: A selection with a suspended player can never be confirmed (property test over
  random selections).
- **SC-005**: Opening the game and every screen switch respond in under 0.5 s on the reference PC.

## Assumptions

- **Textual** (MIT licence) is the TUI framework. It runs in Windows Terminal and the classic
  console and has a test pilot for scripted UI tests. The plan justifies the dependency
  (Constitution: new dependencies are justified).
- **In-match decisions** (half-time changes, tactics) are not in 005. The owner picked the live
  feed without them, and tactics are spec 006.
- **Player "stars"** are relative to the squad (FM's team-relative stars). The exact mapping is set
  in the plan.
- **Season statistics** come from the match reports of the current season.
- **The user's club being relegated** is out of scope (owner).
