# Feature Specification: Competitions and Calendar

**Feature Branch**: `002-competitions-calendar`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Competitions and calendar (Milestone 0, roadmap 002). Competition rules defined as data (each state has its own rules); first implemented ruleset: real FMF Campeonato Mineiro 2026 format (12 clubs, 3 groups of 4, cross-group single round 8 matchdays, 3 group winners + best 2nd to two-leg semifinals with penalties on aggregate tie, single final at a neutral state stadium, Troféu Inconfidência for 5th-8th overall, 2 worst relegated to Módulo II). Seeded FMF-style group draw from season seed (derived from career master seed). Full-year day-by-day calendar with only the Mineiro populated and reserved windows for national competitions; match dates generated from realistic rules (weekends/midweeks, minimum rest ~66h). Standings with tiebreakers, overall classification, advancing the season day by day in memory using a clearly temporary placeholder result simulator (replaced by spec 003). CLI to view groups, fixtures, calendar, tables, bracket and outcomes."

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's competition
rules and calendar handling (rules as data per nation/state; day-by-day progression).

**Real-world reference**: the FMF Campeonato Mineiro 2026 format as reported by the press
([Lance](https://www.lance.com.br/futebol-nacional/grandes-classificam-e-equipe-de-serie-b-cai-veja-as-definicoes-da-primeira-fase-do-campeonato-mineiro.html),
[Flashscore](https://www.flashscore.com.br/noticias/futebol-mineiro-guia-do-campeonato-mineiro-2026-regulamento-times-grupos-e-onde-assistir/tfUf0gJr/),
[Itatiaia](https://www.itatiaia.com.br/esportes/futebol/futebol-nacional/campeonato-mineiro/fmf-confirma-retorno-da-final-unica-para-o-campeonato-mineiro-de-2026/),
retrieved 2026-10-02). Points not confirmed in those sources are listed under Assumptions and must
be checked against the official FMF regulation before this ruleset is called "faithful".

## User Scenarios & Testing *(mandatory)*

The single user is the owner. Until a UI exists (spec 005), every scenario is exercised through
the core's command-line interface (Constitution III).

### User Story 1 - Start a Mineiro season (Priority: P1)

The owner starts a new season for a given year with the 12 sample clubs. The game draws the
three groups the FMF way (the three strongest clubs head one group each, the rest come from
pots), builds the first-phase fixtures (each club meets the 8 clubs of the other two groups once,
4 at home and 4 away) and places every match on a real date in January–March with a venue. The
owner looks at the groups, the fixture list and the dates.

**Why this priority**: everything else in the season (results, tables, knockout, outcomes) needs
groups, fixtures and dates first. It is also the first moment the game "feels like a season".

**Independent Test**: start a season with a fixed seed on the sample world and check the groups,
fixtures, home/away balance, dates and rest periods, with no results played.

**Acceptance Scenarios**:

1. **Given** the sample world and a career seed, **When** the owner starts the 2027 season,
   **Then** 3 groups of 4 are drawn, each headed by one of the three highest-reputation clubs.
2. **Given** the drawn groups, **When** the fixtures are built, **Then** each club has exactly 8
   first-phase matches, one against each club of the other two groups, 4 at home and 4 away, and
   never meets a club from its own group.
3. **Given** the fixtures, **When** dates are assigned, **Then** all 8 first-phase matchdays fall
   inside the Mineiro window, every club plays once per matchday, and no club plays two matches
   less than 66 hours apart.
4. **Given** the same career seed and year, **When** the season is started again, **Then** the
   draw, fixtures and dates are identical (Constitution II). A different seed gives a different
   draw.

---

### User Story 2 - Play the season day by day (Priority: P2)

The owner advances the calendar one day at a time (or to a chosen date). On each matchday the
day's matches get results from a placeholder simulator, clearly labelled as temporary until the
real match engine arrives (spec 003). Group tables and the overall classification update after
each day, with the FMF tiebreakers. When the first phase ends, the game qualifies the three group
winners and the best second-placed club for the semifinals, the clubs placed 5th–8th overall for
the Troféu Inconfidência (any semifinalist among them is skipped and the next-placed club takes the
spot), and marks the two worst clubs as relegated to Módulo II. The knockout rounds are
paired, dated and played, including penalty shootouts where needed. The season ends with a
Mineiro champion, an Inconfidência winner and the two relegated clubs recorded.

**Why this priority**: it turns a fixture list into a playable season, which spec 005 builds on.

**Independent Test**: with a fixed seed, advance through the whole season and check that every
stage happens in order and every outcome follows the rules; check tiebreakers on hand-built
result sets.

**Acceptance Scenarios**:

1. **Given** a started season, **When** the owner advances to the first matchday, **Then** that
   day's 6 matches get results and the group tables and overall classification reflect them;
   advancing over a day without matches changes nothing except the date.
2. **Given** clubs level on points, **When** the table is ordered, **Then** the tiebreakers apply
   in the ruleset's order (see FR-012), and the order is the same every time.
3. **Given** the end of the first phase, **When** qualification is decided, **Then** the three
   group winners and the best second-placed club (compared across groups) reach the semifinals,
   the clubs placed 5th–8th overall enter the Troféu Inconfidência (a semifinalist in that range
   is skipped and replaced by the next-placed club, so no club is ever in both tracks), and
   11th–12th overall are relegated.
4. **Given** the semifinalists, **When** they are paired, **Then** the best campaign meets the
   4th best and the 2nd meets the 3rd, over two legs with the better campaign at home in the
   second leg; a level aggregate goes straight to penalties (no advantage).
5. **Given** the two finalists, **When** the final is played, **Then** it is a single match at the
   neutral state stadium; a draw goes to penalties.
6. **Given** the Inconfidência semifinals and final, **When** a tie is level, **Then** it is
   decided by points across the two legs and then by the better first-phase placing (no
   penalties). The Inconfidência final may be played after the Mineiro window (its second leg
   falls the weekend after the Mineiro final).
7. **Given** a finished season, **When** the owner views the outcomes, **Then** the champion,
   runner-up, Inconfidência winner and the two relegated clubs are shown, and every result shown
   as coming from the placeholder simulator says so.

---

### User Story 3 - Each state has its own rules (Priority: P3)

The owner (or a later spec) describes a competition's format as data: participants, groups and
who plays whom, number of rounds, points, tiebreaker order, qualification and relegation places,
knockout rounds (one or two legs, home advantage, how level ties are decided), venues and date
window. The Mineiro 2026 rules are the first such description. A second, different state format
can be added without changing the game itself. An invalid description is rejected with a clear
report.

**Why this priority**: the owner wants every state to keep its own rules; v1 adds the other
Estaduais and the Brasileirão. Proving the rules are data now avoids a rewrite.

**Independent Test**: load a second, deliberately different test ruleset (e.g. a single
round-robin with a two-leg final and different tiebreakers) and play a full season with it; load
broken rulesets and check each is rejected with the reason.

**Acceptance Scenarios**:

1. **Given** the Mineiro 2026 ruleset, **When** it is loaded, **Then** it validates and drives
   US1 and US2 with no Mineiro-specific logic outside the ruleset.
2. **Given** a second test ruleset with a different structure, **When** a season is played with
   it, **Then** it completes with outcomes that follow that ruleset.
3. **Given** a ruleset with an impossible structure (e.g. 13 clubs in 3 groups of 4, a
   qualification place beyond the number of clubs, an unknown tiebreaker), **When** it is loaded,
   **Then** it is rejected and every problem is listed.

---

### User Story 4 - See the whole year (Priority: P4)

The owner views the season calendar for the whole year, day by day or month by month: the
Mineiro dates (with matchday, stage and fixtures), plus reserved windows where national
competitions and international breaks will go later, shown as empty/reserved.

**Why this priority**: the career is day by day like FM; seeing the year frames what comes after
the Estadual even before those competitions exist.

**Independent Test**: start a season and list the calendar for January–December; check that every
Mineiro date appears, reserved windows are marked, and no Mineiro match falls inside a window
that the ruleset says it must avoid.

**Acceptance Scenarios**:

1. **Given** a started season, **When** the owner lists the calendar for the year, **Then** every
   day from 1 January to 31 December is addressable, Mineiro matchdays show their fixtures, and
   reserved windows are labelled.
2. **Given** a reserved window marked "no state matches", **When** dates are generated, **Then**
   no Mineiro match is placed inside it.

### Edge Cases

- Several clubs level on every tiebreaker except the final "draw" criterion: the order is decided
  by a seeded draw, recorded so a replay gives the same order.
- Head-to-head between clubs that never met (cross-group play means clubs in the same group never
  meet): the criterion is skipped for that comparison.
- Best second-placed club across groups when the groups compare clubs that never met: overall
  criteria only (no head-to-head).
- A three-way tie in a group: tiebreakers apply to the tied set as a whole; head-to-head is used
  only when exactly two clubs are tied (as stated in the ruleset).
- Penalty shootout that is still level after 5 kicks each: sudden death until decided.
- The season is started with fewer or more clubs than the ruleset requires: refused with a clear
  message naming the expected number.
- A club unable to fit its matches in the window with the minimum rest: date generation fails
  with a clear message rather than producing an illegal calendar.
- Advancing past the last day of the year: refused (the next season is spec 004's game loop).
- Up to three semifinalists (weak groups' winners) can rank 5th–8th overall: each is skipped
  for the Inconfidência and replaced by the next-placed eligible club, which in extreme cases
  may reach 11th (a relegated club can still play the Inconfidência; to be confirmed by FMF).
- A season year outside the ruleset's validity range: refused with a clear message.
- The neutral final stadium is also a club's home stadium (not the case in the sample world):
  still treated as neutral, as in the real Mineirão case.

## Requirements *(mandatory)*

### Functional Requirements

**Competition rules as data**

- **FR-001**: Competition formats MUST be described as data (a ruleset), not code. A ruleset
  declares: identity (name, state, the edition of the regulation it follows, and the range of
  season years it is valid for: `valid_from` and an optional `valid_to`), number of participants,
  stages in order, and for each stage its structure, matching, scoring, ordering and outcomes.
  Starting a season in a year outside that range MUST be refused with a clear message.
- **FR-002**: A ruleset MUST support at least these stage types: group stage (with "play own
  group", "play other groups" or "play everyone" matching, single or double round), and knockout
  rounds (single match or two legs).
- **FR-003**: A ruleset MUST declare points per result (Mineiro: 3 / 1 / 0), the tiebreaker
  order, which places qualify where, relegation places, and side competitions fed by places
  (Mineiro: Troféu Inconfidência for places 5th–8th, skipping clubs already in another track).
  A ruleset MUST NOT be able to put a club in two tracks at once: entrant rules taken from places
  declare which tracks' entrants they exclude, and validation rejects overlapping definitions.
- **FR-004**: A ruleset MUST declare knockout details: pairing rule (e.g. best vs worst campaign),
  which side hosts the deciding leg, how level ties are decided (penalties; or points across legs
  then better placing; or other declared criteria) and the venue rule (home grounds or a named
  neutral stadium).
- **FR-005**: A ruleset MUST declare its date window and calendar constraints (earliest and
  latest dates, allowed weekdays, minimum rest between a club's matches, windows to avoid), and
  which stages may run past the window end (Mineiro: only the Inconfidência final).
- **FR-006**: Loading a ruleset MUST validate it and report every problem at once (structural
  impossibilities, unknown criteria, places out of range, inconsistent stage references).
- **FR-007**: The repository MUST include the Mineiro 2026 ruleset and at least one other test
  ruleset with a different structure, both passing validation.

**Season start: draw, fixtures, dates**

- **FR-008**: Each career has a master seed; each season's seed MUST be derived deterministically
  from the master seed and the season year.
- **FR-009**: The group draw MUST follow the ruleset's draw rule. Mineiro: seeded pots by club
  reputation (pot 1 = the three highest; ties broken by club identifier), one club per pot per
  group, drawn with the season seed.
- **FR-010**: Fixtures MUST follow the stage matching. Mineiro first phase: each club plays each
  club of the other two groups once (8 matches), with home and away balanced 4–4, and every club
  playing exactly once per matchday.
- **FR-011**: Match dates MUST be generated from the ruleset's calendar constraints: weekend dates
  preferred, midweek dates used when needed to fit the window, every club rested at least the
  minimum (Mineiro: 66 hours), no matches in avoided windows. Knockout dates follow the first
  phase in order. Each match gets a kick-off time and a venue (home club's stadium, or the neutral
  stadium when the ruleset says so).

**Tables and tiebreakers**

- **FR-012**: Group tables and the overall classification MUST be ordered by points and then by
  the ruleset's tiebreakers. Mineiro default order: (1) wins, (2) goal difference, (3) goals
  scored, (4) head-to-head result (only when exactly two clubs are tied and they met), (5) fewer
  red cards, (6) fewer yellow cards, (7) seeded draw. Unavailable data for a criterion (e.g. no
  card data from the placeholder simulator) makes that criterion neutral, never an error.
- **FR-013**: Tables MUST show played, wins, draws, losses, goals for/against, goal difference,
  points and the place, and MUST mark qualification and relegation zones once they are decided.
- **FR-014**: "Best second-placed club" and the overall classification MUST compare clubs across
  groups using the ruleset's criteria (head-to-head skipped when clubs did not meet).

**Playing the season**

- **FR-015**: The season MUST advance one day at a time or up to a given date. Each advanced day
  plays all matches dated that day, in kick-off order, then updates tables and triggers any stage
  transition (qualification, pairing, dating of the next round, outcomes).
- **FR-016**: Until spec 003, results MUST come from a placeholder simulator that uses only club
  strength (from 001's derived abilities), home advantage and the season seed. It MUST be
  replaceable through a single, documented result-provider entry point, and every result it
  produces MUST be labelled as placeholder in outputs.
- **FR-017**: Knockout ties MUST be resolved per the ruleset, including penalty shootouts (5 kicks
  each, then sudden death) whose kick-by-kick outcome is recorded.
- **FR-018**: At the end of the competition the season MUST record: champion, runner-up,
  semifinalists, side-competition winner (Troféu Inconfidência), relegated clubs (to Módulo II),
  and the final classification.

**Calendar**

- **FR-019**: The season calendar MUST cover every day of the year. Each day may carry matches,
  stage events (draw, qualification, relegation decided) and reserved-window labels.
- **FR-020**: The calendar MUST include reserved windows for later competitions (Brasileirão,
  Copa do Brasil, international dates) as labelled, empty periods; their dates come from data,
  not code. Windows can be fixed (month-day ranges), set per year (e.g. FIFA dates, which change
  every year), or computed from Easter (Carnival, Holy Week). Only the Mineiro is populated in
  this spec.
- **FR-020a**: Carnival MUST be labelled in the calendar every year (Saturday to Ash Wednesday),
  and no state match may be scheduled on Carnival Monday or Tuesday (owner's decision).

**Viewing (CLI)**

- **FR-021**: The owner MUST be able to view, from the CLI and in pt-BR: the groups, the fixture
  list (by matchday or by club), a group table, the overall classification, the knockout bracket,
  the outcomes, the calendar for a month or the year, and the current date; and to start a season
  and advance days.

### Key Entities

- **Ruleset**: the data description of a competition's format (stages, matching, scoring,
  tiebreakers, qualification/relegation places, knockout rules, venues, date window).
- **Competition Season**: one instance of a ruleset in a year: participants, draw, stages,
  matches, current state, outcomes.
- **Stage**: a group stage or knockout round inside a competition season, in order.
- **Group**: a set of clubs within a group stage, with its table.
- **Match**: two clubs, a date and kick-off time, a venue, a stage/leg reference, and (once
  played) a result with its source (placeholder now), goals, cards if available, and penalty
  shootout if any.
- **Table / Classification**: ordered standings with the tiebreaker trail that produced the order.
- **Season Calendar**: every day of the year with its matches, events and reserved windows.
- **Reserved Window**: a labelled date range kept for a future competition or international break.
- **Outcome**: champion, runner-up, side-competition winner, qualifiers and relegated clubs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over 1,000 seasons with different seeds, 100% complete with a valid outcome:
  exactly one champion, two finalists, four semifinalists, four Inconfidência participants and
  two relegated clubs, all consistent with the final tables.
- **SC-002**: The same career seed and year produce the identical season (draw, dates, results,
  outcomes) 100% of the time.
- **SC-003**: In every generated season, each club plays exactly 8 first-phase matches (4 home,
  4 away) against the 8 clubs of the other groups, all inside the window, with no club ever
  playing twice within 66 hours.
- **SC-004**: On at least 10 hand-built tiebreak scenarios (two-way, three-way, cross-group best
  second, head-to-head skipped, full draw), the table order matches the expected order 100% of
  the time.
- **SC-005**: Starting a season and playing it to the end takes under 2 seconds on the reference
  PC with the placeholder simulator.
- **SC-006**: A second, structurally different ruleset plays a full season with no change to the
  game itself, and each of at least 6 deliberately broken rulesets is rejected with its reason.
- **SC-007**: The owner can see any table, the bracket, the outcomes or a month of the calendar
  with one command.

## Assumptions

- **Scope**: only the Mineiro (Módulo I) is played. Módulo II, other Estaduais, Copa do Brasil,
  Brasileirão and continental cups come later; here they are at most reserved calendar windows.
  Relegation is recorded as an outcome; moving clubs between divisions next season is spec 004 or
  later. Copa do Brasil and Série D places from the Mineiro are out of scope (owner's choice).
- **Placeholder simulator**: not calibrated and not a realism target (Constitution I applies to
  spec 003's quick sim). It produces scores only (no cards, no events). Its outputs are always
  labelled placeholder.
- **Unconfirmed details of the real 2026 regulation** (to be checked against the official FMF
  regulation, then the ruleset updated if needed):
  - tiebreaker order (FR-012 uses the order customary in Brazilian state regulations);
  - semifinal pairing 1st×4th / 2nd×3rd by first-phase campaign, better campaign hosting the
    second leg;
  - Troféu Inconfidência entrants (places 5–8 skipping semifinalists, vs. "best 4 not in the
    semifinals"), pairing (5th×8th, 6th×7th), and its final being two legs with the same tie rule
    as its semifinals and played after the Mineiro final;
  - the final going to penalties when level;
  - relegation by first-phase overall classification.
- **Mineiro window**: from the second weekend of January to the first weekend of March, about 11
  match dates for the main competition (8 first phase + 2 semifinal legs + final), consistent with
  the CBF's limit on Estadual dates. Inconfidência legs share the knockout dates.
- **Fictional neutral stadium**: a state stadium in the fictional capital is added to the sample
  data as the Mineirão equivalent (the real Mineirão is not used).
- **Kick-off times**: plausible defaults (e.g. 16:00 weekends, 19:30/21:30 midweek); TV-driven
  scheduling is out of scope.
- **Season state lives in memory** in this spec; saving it is spec 004.
- **Participants**: in M0 they are the clubs of the ruleset's state in the sample world. From v1,
  participants come from the previous season's outcomes (promotion/relegation), which is spec 004
  or later.
- **Draw pots by reputation**: the real FMF draw uses its own ranking; club reputation is the M0
  stand-in until a ranking exists.
- **Regulation edition vs. season**: the bundled ruleset follows the 2026 FMF regulation and is
  valid from the 2026 season onward until a new regulation file replaces it.
- **Rest and kick-offs are coupled**: with 66 h minimum rest, a midweek 21:30 kick-off leaves
  only 30 minutes of margin before a Saturday or Sunday 16:00 kick-off; changing either value
  must be re-validated (the scheduler enforces it).
