# Feature Specification: Godot Desktop Client

**Feature Branch**: `007-godot-client`

**Created**: 2026-10-05

**Status**: Draft

**Input**:
- Roadmap 010, "Local API contract + Godot desktop client". It moves ahead of the positional
  engine, the match report and the assistant: on 2026-10-04 the owner said he expects to play
  in Godot this week.
- Scope: everything the terminal UI (005) and the Tactics screen (006) do, in a Windows desktop
  window, plus the versioned local API contract that Constitution III requires.

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's desktop
layout: a left-hand menu, a top bar with the date and the Continue button, panels and tables,
mouse and keyboard.

## Design decisions (recommendations, recorded for the owner)

The owner asked to keep going while he was away; his standing rule is that he follows the
recommendation. Each choice below is reversible and listed for his review.

1. **Same game as the terminal**: the client has the same screens and the same flow as the
   terminal UI (005) plus the Tactics screen (006). Nothing is cut and nothing new is invented,
   except two screens a desktop game needs: starting a new career, and opening a saved one.
2. **No terminal needed**: the owner starts the game with one double-click. The core starts and
   stops with the window, and no console window is shown.
3. **The contract is the only door**: the client sends requests and shows answers. Every rule
   stays in the core, and every request maps to a facade function. The contract is versioned,
   documented and tested from the core's side.
4. **Mouse first, keyboard too**: buttons, lists and tables work with the mouse, as in FM. The
   terminal UI's main shortcuts keep working (Space continues, X opens tactics, Esc goes back).
5. **Local only**: nothing leaves the machine. The client and the core talk only to each other,
   with no network service another program could reach.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Play a season in the desktop window (Priority: P1)

The owner double-clicks the game and the home screen opens. It shows:
- the date and the club;
- the next match;
- the club's table position;
- the latest news.

From the left-hand menu he moves between screens, and the Continue button advances the game.
Before each of his matches the game stops on team selection. After he confirms, the match is
played with a live feed, and then the stats are shown. The season goes on to its end, and then
into the next season.

**Why this priority**: it is the reason for the feature: play the Milestone 0 game in a real
game window.

**Independent Test**: an automated client session:
1. opens a career;
2. continues to the first match;
3. confirms the proposed XI;
4. lets the match feed finish;
5. continues to the season end.

No screen fails, and the season's results equal those of the same career played through the core
alone.

**Acceptance Scenarios**:

1. **Given** a saved career, **When** the game starts, **Then** the home screen shows the date, the
   club, the next match, the table position and the latest news.
2. **Given** the home screen, **When** the owner presses Continue, **Then** the game advances to
   the next stop. A user match day opens team selection, and events go to the news.
3. **Given** team selection, **When** the owner confirms, **Then** the match plays as a live feed
   at the chosen speed, and then the stats are shown.
4. **Given** a finished season, **When** the owner continues, **Then** the season's outcome is
   shown and the next season starts.
5. **Given** the window is closed, **When** the game is started again, **Then** the career resumes
   where it was (saved on quit).

---

### User Story 2 - Choose the team and the tactic (Priority: P1)

**Team selection**:
- the assistant's XI and bench, shown on the formation;
- swapping players;
- changing the formation;
- asking the assistant again;
- confirming.

The rules are the core's: suspended players are refused, and the owner is warned when no
goalkeeper starts.

**Tactics screen**:
- the out-of-possession formation;
- the mentality (7 levels);
- the team instructions grouped by phase;
- the in- and out-of-possession roles per slot, with each player's suitability;
- player instructions, with the ones locked by a role marked;
- set-piece takers and setups.

Confirming saves the tactic. A formation change that loses the owner's own choices is
reported.

**Why this priority**: these are the decisions the game is about. Without them the window is a
spectator.

**Independent Test**: in an automated session:
- swap two players, confirm, and check the match is played with that XI;
- change the mentality and a team instruction, confirm, and check the next match report records
  that tactic;
- try a suspended player and see the refusal.

**Acceptance Scenarios**:

1. **Given** team selection, **When** the owner swaps a bench player into the XI, **Then** the
   match is played with exactly that XI.
2. **Given** a suspended player, **When** the owner tries to start him, **Then** the swap is
   refused, with the core's message.
3. **Given** the Tactics screen, **When** the owner changes a setting and confirms, **Then** the
   tactic is saved with the career and used in his next match.
4. **Given** custom roles, **When** the owner confirms a selection in another formation, **Then**
   he is told which positions lost their choices.
5. **Given** a role that locks an instruction, **When** the owner tries to change it, **Then** the
   change is refused and the lock is shown.

---

### User Story 3 - Follow the world: squad, tables, calendar, news (Priority: P2)

The owner opens:
- the squad, with a player profile (attributes by group, position, form, discipline);
- the competition tables and fixtures;
- the calendar by month;
- the news.

**Why this priority**: an FM-style game is also about following the world. These screens exist
in the terminal UI and must not be lost.

**Independent Test**: in an automated session, open each screen at three points of a season
(start, middle, end). Each one shows the same content as the core returns for that date.

**Acceptance Scenarios**:

1. **Given** the squad screen, **When** the owner opens a player, **Then** his profile shows
   attributes by group, positions and current status (suspended or available).
2. **Given** the tables screen, **When** a round has been played, **Then** the table and the
   fixtures show the new results.
3. **Given** the calendar, **When** the owner moves between months, **Then** each day shows its
   matches and events.

---

### User Story 4 - Start or open a career without the terminal (Priority: P2)

When the game opens, the owner can:
- start a new career: choose a name and one of the clubs;
- open any saved career, which the game lists with its club, date and season.

**Why this priority**: in the terminal version, careers were created from the command line. A
desktop game must not need it.

**Independent Test**: in an automated session, create a career, close the game, reopen it, and
open the career from the list.

**Acceptance Scenarios**:

1. **Given** no careers, **When** the game opens, **Then** it offers to start a new career.
2. **Given** a new career's name and club, **When** the owner confirms, **Then** the career is
   created and opens on the home screen.
3. **Given** an invalid or duplicate name, **When** the owner confirms, **Then** the core's
   message is shown and nothing is created.
4. **Given** saved careers, **When** the game opens, **Then** they are listed, most recent first,
   and any of them can be opened.

---

### Edge Cases

- **The core fails to start** (Python missing or broken): the window shows a clear PT-BR message
  explaining what is wrong, instead of an empty screen.
- **The core stops during play**: the client reports it and offers to restart. A request is
  never left waiting forever.
- **A long request** (continuing many days, or a whole season): the window stays responsive and
  shows progress. It never freezes.
- **Version mismatch** between the client and the core: the client refuses to run and names
  both versions, rather than misbehaving.
- **A save from an older format** opens through the core's migrations, as in the terminal.
- **A small window**: the layout stays usable down to 1280×720.
- **Two copies of the game**: the second one must not corrupt the first one's save. Saves are
  written by the core only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The client MUST provide every screen and action of the terminal UI (005) and the
  Tactics screen (006): home, Continue, team selection, tactics, match day (live feed, then the
  stats), squad and player profile, tables and fixtures, calendar, news, and save on quit.
- **FR-002**: The client MUST provide new-career creation (name and club) and a list of saved
  careers to open.
- **FR-003**: The client MUST hold no game rules. Every decision goes to the core through the
  local API contract, and the client shows the result or the core's message.
- **FR-004**: The local API contract MUST be versioned and documented, and MUST cover every
  action in FR-001 and FR-002. Every request maps to a core facade function.
- **FR-005**: The client and the core MUST check that their contract versions are compatible at
  start, and refuse to run otherwise, naming both versions.
- **FR-006**: The game MUST start with one double-click and show no console window. The core's
  lifetime follows the window's.
- **FR-007**: Communication MUST stay on the machine, with no network service reachable by other
  programs.
- **FR-008**: Long operations MUST NOT freeze the window. The client shows that work is in
  progress.
- **FR-009**: Every user-facing text MUST be in PT-BR. Text coming from the core is shown as is
  (it is already localised); the client's own labels are localised in the client.
- **FR-010**: The core's error codes and messages MUST reach the owner unchanged (e.g. a refused
  swap, an invalid tactic, a duplicate career name).
- **FR-011**: Playing through the client MUST give exactly the same results as the core alone
  for the same career and decisions (determinism, Constitution II).
- **FR-012**: The layout MUST be usable from 1280×720 upward, with mouse and keyboard. Space
  continues, X opens tactics and Esc goes back.

### Key Entities

- **Local API contract**: the versioned list of requests and answers between client and core:
  each request's name, inputs, outputs, error codes and the version.
- **Client session**: the running window, connected to one core process and one open career.
- **Screen view**: what a screen shows, built by the core (lists, tables, texts) and drawn by
  the client.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A whole season can be played through the client from a double-click, without using
  a terminal, in an automated session and by hand.
- **SC-002**: The season's results through the client are identical to the core alone for the
  same career, seed and decisions (100% of matches).
- **SC-003**: Every request in the contract has an automated test on the core side, and the
  contract's version is checked at start (100% of requests covered).
- **SC-004**: Screens open in under 0.5 s on this Windows PC. Continuing to the next stop takes
  no longer than in the terminal UI, plus 0.2 s. A whole-season continue shows progress and never
  freezes the window.
- **SC-005**: Every screen of the terminal UI has a counterpart in the client (a parity checklist
  in the quickstart, all items ticked).

## Assumptions

- **Godot 4.7** (the current stable release) is the client engine, as the constitution decided.
  It is fetched as a portable download into the project, with no system install. Exporting a
  standalone executable is out of scope. The game runs from the project with the portable
  editor, started by a launcher.
- **Python and the core** are those of the repo's virtual environment. The launcher uses them, as
  the terminal UI does.
- **Visual style**: a clean FM-like layout with the default theme, lightly styled. Badges, kits,
  photos and animation are later work.
- **The match view is text** (a live feed and the stats). 2D and 3D views come with the
  positional engine.
- **The terminal UI stays** as a supported client. Both clients use the same contract or facade,
  with no duplicated rules.
- **Windows only** (owner decision, 2026-10-03).
