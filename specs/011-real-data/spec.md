# Feature Specification: Real Data for Minas Gerais Clubs

**Feature Branch**: `011-real-data`

**Created**: 2026-10-07

**Status**: Draft

**Input**: Owner request (2026-10-07): "real football database", with these owner decisions:
- player ability comes from our own **attribute-synthesis model**;
- **Minas Gerais first**;
- squad sources are **not decided**: the owner asked to "spend a day collecting" how real data can be obtained before choosing.

Roadmap 011 (Milestone 1 data). It also carries over from 001:
- tolerant reading of files re-saved by pt-BR Excel (format v1.1);
- the field-level audit trail.

## Context

The game runs today on a fictional sample world of 12 clubs. The owner wants the real thing,
starting with the clubs of the Campeonato Mineiro.

**FM is the benchmark.** Football Manager's database is built by about 1,300 human researchers
who rate every player by hand. We cannot do that. Our equivalent has two parts:
- a **synthesis model**: public facts about a player (league level, club strength, playing time and
  match stats, age, position, market value where known) produce an overall level, and the
  FM-style attributes are spread around it by position;
- an **owner review step**: the owner corrects what looks wrong, and every correction survives
  later re-imports.

**Data rights are a constitution matter (Principle VI):**
- real data lives only in the private `manager-data` repository, never in this public one;
- every imported record carries its provenance;
- tests never depend on private data.

**No other game's ratings are copied**, whether from FM, Brasileirinho FC or SoFIFA. Ability is
always our own synthesis.

## Clarifications

### Session 2026-10-07 (owner)

- Q: Where does player ability come from? → A: The synthesis model (our own, tunable).
- Q: Which clubs first? → A: Minas Gerais: the Campeonato Mineiro, Módulo I first.
- Q: Where do squads come from? → A: Not decided. Survey the sources first, then the owner
  picks ("spend a day collecting").
- Q: ogol has the most complete Mineiro squads but publishes no terms of use. Its content is "all
  rights reserved", and as a Portuguese company it is covered by the EU database right. How should
  we use it? → A (owner, 2026-10-07): **use it now, gently**:
  - private use only, never published;
  - Mineiro clubs only;
  - at least a few seconds between requests;
  - an honest user agent;
  - robots obeyed;
  - every page cached in the private data repository, so nothing is fetched twice.
- Q: Scope beyond Minas Gerais? → A (owner, 2026-10-08): keep the 4 s pace. Scope grows in
  order: Minas Gerais (Módulo I, then II), then the rest of Brazil, then the rest of South
  America, then the world. Each step is cached and reviewed before the next. Active players only;
  monthly refresh.
- Q: Other regions' sources? → A (owner, 2026-10-08): survey them the same way as Brazil
  (coverage, freshness, terms, robots, fields) before collecting there.
- Q: Which divisions? → A (owner, 2026-10-08, the recommendation): Brazil Série A to D; South
  America: each country's top two divisions.
- Q: South America, given no open source with clear permission? → A (owner, 2026-10-08): stop at
  Brazil and the big leagues for now. South America waits until permissions are settled (asking
  league or federation bodies for private, non-commercial use). Brazil continues.
  - Rough volume: about 11.6 s per ogol page measured (not 4 s: server time dominates). Módulo I
    is about 2 h. South America's top divisions are about 20 h more. The whole world is about a
    week of unattended running, spread over days.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose the sources with evidence (Priority: P1)

Before any import is built, the owner receives a source survey. For every candidate source of club
and player facts it records:
- which Mineiro clubs it covers;
- how fresh its data is;
- what its terms of use and robots rules allow;
- which fields it provides.

The survey ends with a recommendation. The owner picks the sources.

Candidates:
- Wikipedia;
- CBF's BID registrations;
- FootyStats CSV downloads;
- zerozero / ogol;
- Transfermarkt;
- FBref;
- SofaScore;
- Brasileirinho FC public pages;
- FM-database mod files.

**Why this priority**: every later story depends on which sources are allowed and good enough. The
owner asked for this first.

**Independent Test**: the survey document exists and covers every candidate with the same fields.
The owner can choose from it without further research.

**Acceptance Scenarios**:

1. **Given** the candidate list, **When** the survey is delivered, **Then** each source has:
   - coverage of the Módulo I clubs, and of Módulo II where known;
   - the date of its newest data;
   - its terms-of-use and robots status, with the exact clause quoted where one applies;
   - the fields it provides, mapped to the game's player and club fields.
2. **Given** a source whose terms forbid automated collection or reuse, **When** it is surveyed,
   **Then** the survey says so plainly, and it is not recommended for automated import.
3. **Given** the survey, **When** the owner picks sources, **Then** the choice is recorded in this
   spec as an owner decision with its date.

---

### User Story 2 - Play with the real Mineiro clubs (Priority: P1)

The owner starts a career with a real Módulo I club. The clubs have their real names, cities,
stadiums and colours, and the client's look follows each club's real colours. Each club has its
current first-team squad, and every player has a real name, age, nationality, positions and
preferred foot.

**Why this priority**: this is the point of the feature. The owner plays with the clubs he knows.

**Independent Test**: build the real Mineiro dataset from the chosen sources, load it, start a
career with any Módulo I club and play a match day.

**Acceptance Scenarios**:

1. **Given** the chosen sources, **When** the import runs, **Then** every Módulo I club appears
   with:
   - its real name, short name and abbreviation;
   - its city, stadium and capacity, and founding year;
   - its primary and secondary colours.
2. **Given** an imported club, **When** its squad is viewed, **Then** every player has:
   - a real name, birth date (or age) and nationality;
   - his positions and preferred foot.
3. **Given** the imported dataset, **When** the game validates it, **Then** it passes the same
   validation as the sample dataset, and every record names its source, retrieval date and import
   version.
4. **Given** the imported dataset, **When** anyone looks at the public repository, **Then** no
   real club or player data is there.

---

### User Story 3 - Believable ability from the synthesis model (Priority: P2)

Every imported player gets an overall level and a full set of FM-style attributes from the
synthesis model. A Módulo I title contender's star is clearly better than a relegation candidate's
squad player. A goalkeeper's attributes look like a goalkeeper's. A 19-year-old prospect differs
from a 33-year-old veteran in the ways football expects.

**Why this priority**: without ability, real names are only labels. The model is how the game
earns realism without anyone's ratings.

**Independent Test**: run the model on the imported Módulo I squads and compare the resulting club
strengths with real outcomes (last seasons' final standings).

**Acceptance Scenarios**:

1. **Given** imported squads with their public signals, **When** the model runs, **Then** every
   player has an overall level and every attribute the game uses, within the game's 1–20 scale.
2. **Given** the clubs' synthesised strengths, **When** they are ranked, **Then** the ranking agrees
   with the clubs' real recent standings to the stated degree (SC-003).
3. **Given** two players of different positions with the same overall level, **When** their
   attributes are compared, **Then** each shows his position's profile: a goalkeeper's reflexes, a
   centre-back's heading and marking, a winger's pace and crossing.
4. **Given** a player with weak signals (few minutes, no market value), **When** the model runs,
   **Then** he still gets a plausible level from his club and league, and his record shows the
   lower confidence.

---

### User Story 4 - The owner corrects, and corrections stick (Priority: P2)

The owner disagrees with a rating, a position or a name, edits it, and later re-imports the data
for a new season. His correction is kept. The audit trail shows which field he changed, from what
value, to what value, and when.

**Why this priority**: this is the human half of the FM benchmark. The model is a first draft, and
the owner's football knowledge makes it right.

**Independent Test**: correct a player's attribute and a club's colour, re-run the import, and
confirm that both corrections remain and the audit trail lists them field by field.

**Acceptance Scenarios**:

1. **Given** an imported player, **When** the owner changes an attribute, **Then** the change is
   recorded at field level: player, field, old value, new value, date.
2. **Given** owner corrections, **When** the import runs again with fresh source data, **Then**
   every correction is kept. Fields he did not touch take the fresh values.
3. **Given** a correction whose player has left the source data (transferred out), **When** the
   import runs, **Then** the correction is kept with the player and reported, never silently
   dropped.

---

### User Story 5 - Módulo II and Excel round trips (Priority: P3)

The import extends to the Módulo II clubs. The owner can open the dataset files in pt-BR Excel,
edit and save them, and the game reads them back without errors (format v1.1, carried over from
001).

**Why this priority**: lower-division coverage completes the Mineiro world. Excel is how the owner
will review hundreds of players.

**Independent Test**: import Módulo II. Then open a dataset file in pt-BR Excel, change a value,
save it, and load the dataset.

**Acceptance Scenarios**:

1. **Given** the Módulo II clubs, **When** the import runs, **Then** they appear with full squads,
   where the sources cover them. Where they do not, the gap is reported per club.
2. **Given** a dataset file re-saved by pt-BR Excel, **When** the game loads it, **Then** it reads
   correctly. Excel's changes are tolerated: separators, decimal commas, date formats, encoding and
   byte-order mark.

### Edge Cases

- **A player on loan:** he belongs to the club he plays for, and the parent club is kept as a fact.
- **Ambiguous player names:** the same name at two clubs, or common nicknames ("Gabriel"). Identity
  comes from more than the name, and the importer flags unresolved duplicates for the owner.
- **Disagreeing sources:** an age or position differs between two sources. The import follows a
  stated precedence and lists every disagreement for review.
- **A club the sources barely cover** (a small Módulo II club): it is imported with what exists, and
  the gap is visible. The game never invents players silently. Placeholders, if used, are flagged
  as such.
- **A source changes its page layout or terms:** the import fails loudly for that source and keeps
  the last good data.
- **Mid-season transfers:** the dataset has a reference date. Re-imports move players and keep the
  owner's corrections.
- **Club colours:** a source gives only one colour, or none. The owner supplies the rest in review,
  and the client's look already copes with any pair.

## Requirements *(mandatory)*

### Functional Requirements

**Sources (US1)**

- **FR-001**: Deliver a source survey covering at least these candidates:
  - Wikipedia;
  - CBF BID;
  - FootyStats;
  - zerozero/ogol;
  - Transfermarkt;
  - FBref;
  - SofaScore;
  - Brasileirinho FC public pages;
  - FM-database mods.

  For each, record coverage of the Mineiro clubs, data freshness, terms of use and robots rules
  (quoting the relevant clauses), and the fields provided, mapped to the game's schema.
- **FR-002**: Recommend sources for clubs, squads and the model's signals, and record the owner's
  choice as a dated decision before any collection tool is built.
- **FR-003**: Automated collection MUST respect each source's robots rules and terms. It MUST
  identify itself honestly, pace its requests, and cache what it fetched, so a re-run does not
  fetch again. A source whose terms forbid automated use is used only by hand, if at all, as the
  owner decides.

**Import (US2)**

- **FR-004**: Import every Módulo I club with:
  - its real identity (name, short name, abbreviation);
  - city and state;
  - stadium and capacity;
  - founding year;
  - primary and secondary colours.

  Then import its current first-team squad.
- **FR-005**: Each imported player MUST have:
  - full and display name;
  - birth date, or age where only that is known;
  - nationality;
  - positions with familiarity;
  - preferred foot;
  - shirt number, where known.
- **FR-006**: Every imported record MUST carry its provenance: source(s), retrieval date and import
  version (Constitution VI). A re-import from the same cached inputs MUST give the same dataset.
- **FR-007**: The imported dataset MUST live only in the private `manager-data` repository and MUST
  pass the game's existing dataset validation. The public repository keeps only the fictional
  sample, and a check MUST fail if real data reaches it.
- **FR-008**: The importer MUST report, per club:
  - players found;
  - fields missing;
  - source disagreements;
  - unresolved identities.

**Synthesis (US3)**

- **FR-009**: Give every player an overall level and every attribute the game uses (1–20 scale),
  from public signals only:
  - league level;
  - club strength;
  - playing time and match stats;
  - age;
  - positions;
  - market value, where known.

  No rating from another game may be an input.
- **FR-010**: Attributes MUST follow position profiles and age curves. Every player's record MUST
  state the model's confidence, from the strength of his signals.
- **FR-011**: The model's parameters MUST be data in the public repository (the method is not
  private, only the data is). They MUST be tested on the fictional sample, so that tests never
  need private data.

**Owner review (US4)**

- **FR-012**: The owner MUST be able to correct any player or club field. Corrections MUST be
  recorded at field level (record, field, old value, new value, date) and MUST survive every
  re-import.
- **FR-013**: The audit trail MUST distinguish source values, model values and owner values, so
  that the origin of any field can be told.

**Coverage and files (US5)**

- **FR-014**: Extend the import to Módulo II clubs. Coverage gaps are reported per club.
- **FR-015**: Read dataset files re-saved by pt-BR Excel (format v1.1). Tolerate:
  - separators;
  - decimal commas;
  - date formats;
  - encoding and byte-order mark.

### Key Entities

- **Source**: a place facts come from. Name, kind, terms and robots status, coverage, freshness,
  fields provided, and the owner's decision.
- **Raw record**: what a source said about a club or player on a date, kept in a cache, so imports
  are reproducible.
- **Club** (existing): now with real identity and colours, and provenance.
- **Player** (existing): now with real identity, plus the synthesis model's overall level,
  attributes and confidence, and provenance per field group.
- **Correction**: one owner change. Record, field, old value, new value, date. It is kept across
  imports.
- **Import run**: one execution. Inputs, version, date, report (FR-008).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The survey covers all nine candidate sources with every FR-001 field filled. The
  owner chooses the sources without further research.
- **SC-002**: 100% of Módulo I clubs are imported with real identity and colours, and each has at
  least 22 first-team players. 100% of records carry provenance.
- **SC-003**: The synthesised club strengths rank the Módulo I clubs in close agreement with their
  real recent standings: a rank correlation of at least 0.7 against the last completed Mineiro.
- **SC-004**: 100% of owner corrections survive a re-import. The audit trail shows each one at
  field level.
- **SC-005**: A full Módulo I re-import from cached inputs takes at most 10 minutes on the
  reference PC, and gives an identical dataset.
- **SC-006**: The public repository contains no real club or player data, and an automated check
  enforces this.
- **SC-007**: A dataset file opened and re-saved in pt-BR Excel loads without errors and with no
  value changed.
- **SC-008**: With the real Mineiro dataset, the quick sim's season outcomes look plausible to the
  owner: the strongest clubs finish near the top and the table's spread is realistic. The game
  remains playable from career start through a match day.

## Assumptions

- The squads are the current ones (2026 season). The game world starts in 2027, as it does now, so
  the first career season uses these squads.
- The Módulo I club list is the 2026 one. Promotion and relegation change it later through the
  game's own seasons, not the import.
- Ages come from birth dates where a source gives them.
- Market value is optional: many Módulo II players have none, and the model must cope.
- Personal use only. The game is never published (owner, 2026-10-02), so real names and badges are
  acceptable. Badges and photos are out of scope for 011.
- The owner reviews in Excel or a text editor. A review screen in the game is out of scope.
- Brasileirinho FC's terms protect its program, screens, texts and original art. Its overall
  ratings are its own work, and they are not used as an input (owner decision 1). Its public
  rosters are surveyed like any other source.
- The calibration targets and gates are unchanged. The real dataset is checked for plausibility
  (SC-008), not used for calibration.
