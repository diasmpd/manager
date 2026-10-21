# Feature Specification: The Assistant's Suggestions

**Feature Branch**: `010-assistant`

**Created**: 2026-10-21

**Status**: Draft

**Input**: Roadmap 010 ("Assistant: suggestions and optional auto-subs"). Owner decisions
(2026-10-21):
- scope now: the suggestions before and between matches: the **opposition report**,
  **team-selection warnings**, **tactic advice against the opponent** and **squad advice**;
- delivery: a **match-day briefing** on the team-selection screen, with one-click "Aplicar" for
  the selection and tactic suggestions, and the opposition report as a **news item** the day
  before the match (FM's inbox).

In-match advice and the optional auto-subs need the live match of spec 008 and come with it (a
later part of 010).

Milestone 0.

## Context

**FM is the benchmark.** FM's assistant manager:
- sends an **opposition report** before each match (the opponent's likely formation and style,
  key players, form, who is unavailable);
- comments on the **team selection** (a player out of position, a better option on the bench, a
  player one booking from a ban);
- offers **tactical suggestions** for the match, which the manager may accept or ignore;
- gives **squad feedback** (positions short of cover, ageing players, youngsters ready).

Constitution V: the assistant's actions are **suggestions by default**. Nothing changes unless
the owner clicks "Aplicar", and an applied suggestion goes through the same core methods as a
change made by hand (Principle III: no rule in the client).

What exists to build on:
- spec 006's AI reads a squad (attack, control, defence; pace, energy, aerial), picks each club's
  **style** and adapts it per match (`tactics.ai.pre_match`). The assistant reads the opponent
  with the same code, and suggests for the owner's side what the AI would do in his place;
- the selection rules and the role suitability (spec 006) and the discipline ledger (spec 004);
- the season's results and scorers, and the derived news of spec 012.

No injury or fitness model exists in Milestone 0, so no advice depends on one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Know the opponent (Priority: P1)

The day before each of his matches, a news item from the assistant gives the opposition report.
On match day the same report heads the briefing on the team-selection screen.

**Independent Test**: stop before a user match; the briefing names the opponent, its likely
style and formation, the strength comparison, three key players, its top scorers so far, its
last five results and its suspended players; the news has the report dated the day before.

**Acceptance Scenarios**:

1. **Given** a match day, **When** the briefing opens, **Then** the report is the opponent's, as
   the AI would play it (its style, its formation).
2. **Given** the opponent has played, **When** the report is written, **Then** form and scorers
   count only matches before the report's day.
3. **Given** the first round, **When** the report is written, **Then** it says there is no form
   yet instead of an empty list.

### User Story 2 - Selection warnings, applied with one click (Priority: P1)

**Independent Test**: a selection with a player out of position and a clearly better bench player
gets both warnings; "Aplicar" on the second makes the swap, and the warning goes.

**Acceptance Scenarios**:

1. **Given** a starter one yellow card from a ban, **Then** the briefing says so (no action).
2. **Given** a starter whose familiarity at his slot is below natural, **Then** a warning names
   him and the slot, with the best natural player available as the suggested swap.
3. **Given** a bench or reserve player clearly better at a slot than its starter, **Then** a
   suggestion offers the swap.
4. **Given** "Aplicar", **Then** the selection changes exactly as by hand, and is kept.

### User Story 3 - Tactic advice against this opponent (Priority: P2)

**Independent Test**: as a big underdog away, the briefing suggests what the AI would do (a more
cautious mentality, a deeper block); "Aplicar" sets that tactic. A player badly suited to his
role gets a better-suited role suggested.

**Acceptance Scenarios**:

1. **Given** the AI's adaptation would change the owner's tactic, **Then** the suggestion lists
   the changes in words and offers the adapted tactic.
2. **Given** an even match, **Then** no adaptation is suggested.
3. **Given** a starter whose role suitability is low and another valid role suits him clearly
   better, **Then** that role is suggested for his slot.

### User Story 4 - Squad advice (Priority: P3)

**Independent Test**: on the sample, the briefing lists positions without cover, ageing regulars
and youngsters ready; a squad advice news item comes at the start of each season.

**Acceptance Scenarios**:

1. **Given** a position line (goalkeeper, centre-back, full-back, midfield, wing, striker) with
   fewer natural players than the club needs, **Then** it is named.
2. **Given** a starter of the owner's XI aged 33 or more, **Then** he is named as ageing.
3. **Given** a player aged 21 or less, out of the owner's XI, who at his best natural position is
   at least as good as the XI's median starter at his, **Then** he is named as ready.

## Requirements *(mandatory)*

- **FR-001**: The core builds the briefing for the career's next user match: the opposition
  report, then the selection, tactic and squad advice. Every text is PT-BR from the catalogue.
- **FR-002**: Each piece of advice has a kind, a severity (`info` or `warning`), its text, and an
  optional action: `swap` (slot, player), `role` (slot, phase, role) or `tactic` (a whole tactic).
- **FR-003**: An action is applied by the client through the existing methods (`selection.swap`
  then `selection.confirm`; `tactic.set_role` or the given tactic, then `tactic.confirm`). The
  assistant never changes anything itself (Constitution V).
- **FR-004**: The opposition report reads the opponent with the AI's own code (spec 006): its
  style, its team sheet and formation, and the same strength figure `pre_match` uses.
- **FR-005**: The tactic advice is the AI's `pre_match` applied to the owner's current tactic for
  this match; a role suggestion needs a suitability gain of at least the threshold in
  `reference/career/assistant.toml`, where every threshold of this spec lives.
- **FR-006**: News: an `assistant` item the day before each user match (its opposition report as
  of that day), and one with the squad advice on the season's first day. Derived, like spec 012's.
- **FR-007**: Deterministic: the same career gives the same briefing and the same news.
- **FR-008**: Contract: `assistant.briefing` (minor version bump).

## Success Criteria *(mandatory)*

- **SC-001**: Every acceptance scenario above is covered by a test on the fictional sample.
- **SC-002**: Applying every suggested action of a briefing yields a valid selection and a valid
  tactic (checked over the first matches of several careers).
- **SC-003**: The owner gets a briefing on every match day and the report in the news, in the
  desktop window.

## Out of scope

- In-match advice and auto-subs (need spec 008's live match).
- Scouting, staff quality and assistant personality (later milestones).
- Training and fitness advice (no such model in Milestone 0).
