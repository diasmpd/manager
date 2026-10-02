# Feature Specification: Core Domain Model

**Feature Branch**: `001-core-domain-model`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Core domain model (Milestone 0, roadmap 001): clubs, players with Football Manager's full attribute set (technical, mental, physical, goalkeeping, hidden) on a 1-20 scale, position familiarity per FM position code, basic squad membership, the data import format (format only; no SoFIFA/Transfermarkt conversion) with provenance, and a fictional sample dataset sufficient to run tests and a Campeonato Mineiro prototype. Formation choice only if needed by spec 005 lineup selection."

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's player and club model.

## User Scenarios & Testing *(mandatory)*

The single user is the owner, who plays the game and also curates its data. Until a UI exists
(spec 005), every scenario is exercised through the core's command-line interface (Constitution III).

### User Story 1 - Explore a ready-made football world (Priority: P1)

The owner loads the built-in fictional sample world. It has 12 clubs, sized and tiered like a
Campeonato Mineiro (a few strong clubs, a mid-table group and small clubs). The owner browses any
club's squad and opens any player's full profile: identity, age, nationality, foot, height,
positions with familiarity, and every FM attribute grouped as FM groups them.

**Why this priority**: every later spec (competitions, quick sim, save, playable season) needs a
coherent world to run against. It also lets the owner judge at a glance whether players "feel
like football players".

**Independent Test**: load the sample world with no other data present, list a club's squad and
show a player's profile. The data is complete, valid and believable (e.g. strikers finish better
than centre-backs on average, goalkeepers have real goalkeeping attributes).

**Acceptance Scenarios**:

1. **Given** a fresh installation, **When** the owner loads the sample world, **Then** 12 clubs
   load, each with a playable squad, and no validation errors are reported.
2. **Given** the loaded sample world, **When** the owner lists a club's squad, **Then** every
   player appears with shirt number, name, age, main position and a position-suitability rating,
   sortable by position.
3. **Given** the loaded sample world, **When** the owner opens a player's profile, **Then** all
   visible attributes appear grouped as Technical / Mental / Physical (Goalkeeping for
   goalkeepers). Hidden attributes appear only in an explicit "debug/curator" view.
4. **Given** the same generator version and seed, **When** the sample world is regenerated,
   **Then** it is identical to the committed sample dataset (Constitution II).

---

### User Story 2 - Import a curated dataset safely (Priority: P2)

The owner prepares a dataset (e.g. real Mineiro clubs, later produced by spec 011) in the
documented import format, with a provenance record saying where it came from. The owner imports
it. Valid data loads. Invalid data is rejected with a precise report listing each problem by
file, record and field, so it can be fixed and re-imported.

**Why this priority**: the real-data pipeline (spec 011) and the private `manager-data` repo depend
on a stable, validated, auditable format. Rejecting bad data up front protects every simulation
downstream.

**Independent Test**: import a known-good dataset (accepted) and a set of deliberately broken
datasets (each rejected with the expected error), using only fictional test fixtures.

**Acceptance Scenarios**:

1. **Given** a dataset with complete, valid records and a provenance record, **When** the owner
   imports it, **Then** all clubs and players load and the provenance is attached to them.
2. **Given** a dataset where one player has an attribute of 23, **When** the owner imports it,
   **Then** the import is rejected and the report names the file, the player identifier, the
   field and the allowed range.
3. **Given** a dataset with several independent errors, **When** the owner imports it, **Then**
   all errors are reported in one pass (not only the first), and nothing is loaded.
4. **Given** a dataset that is valid but has implausible values (e.g. an outfield player with
   goalkeeping attributes of 18, or a 41-year-old with pace 19), **When** the owner imports it,
   **Then** it loads, and a warnings section lists each implausibility for human review.
5. **Given** a dataset with no provenance record, **When** the owner imports it, **Then** the
   import is rejected (Constitution VI).

---

### User Story 3 - Find who can play where (Priority: P3)

When looking at a squad, the owner asks which players can play a given position (e.g. "who can
play DC?") and gets them ranked by suitability for that position. Suitability combines the
attributes that matter for the position with the player's familiarity with it, as in FM, where an
unfamiliar player is noticeably weaker. The owner can also ask for an automatically suggested
best XI for a given set of positions.

**Why this priority**: spec 005 (playable season) needs lineup selection and a sensible default
XI. The ranking is also the first visible sign that attributes mean something.

**Independent Test**: on the sample world, ask for the ranking at each position and for the
suggested XI, and check them against expected outcomes on hand-built fixtures.

**Acceptance Scenarios**:

1. **Given** a squad, **When** the owner asks for the ranking at a position, **Then** players are
   ordered by suitability, and a natural player at that position outranks an equally-attributed
   player who is unfamiliar with it.
2. **Given** a squad and a set of 11 positions, **When** the owner asks for the best XI, **Then**
   each player is used at most once, exactly one goalkeeper fills the GK slot, and the total
   suitability is the best possible. A greedy pick that leaves a weak player in a key slot is not
   acceptable.
3. **Given** a squad with no fit goalkeeper, **When** the best XI is requested, **Then** the
   system still returns a lineup (the most suitable outfield player in goal) and flags it.

---

### User Story 4 - Edit and round-trip data (Priority: P4)

The owner exports any loaded dataset back to the import format, edits it by hand (e.g. fixes a
player's foot or adds a position) and re-imports it. Nothing is lost or altered except the edits.

**Why this priority**: the owner is used to curating data in spreadsheets. Round-tripping makes
the data maintainable without special tools and keeps `manager-data` diffs readable.

**Independent Test**: export the sample world, re-import it, and compare: the two must be
identical. Then change one field and check that only that field differs.

**Acceptance Scenarios**:

1. **Given** a loaded dataset, **When** it is exported and re-imported unchanged, **Then** the
   result is identical to the original, including provenance and external references.
2. **Given** an exported dataset, **When** the owner edits a single attribute and re-imports it,
   **Then** only that attribute differs, and the provenance records that the data was manually
   edited.

### Edge Cases

- Two players with the same name in one club (common in Brazil, e.g. two "Gabriel"s): allowed.
  Players are told apart by identifier and shown with a disambiguating display name.
- Player with no club (free agent): allowed. They appear in a free-agent pool.
- Duplicate shirt numbers in one club: rejected. Missing shirt number: allowed (unassigned).
- Player referencing a club that does not exist in the dataset: rejected.
- Duplicate identifiers (club or player): rejected.
- Player with no position at familiarity ≥ 15 (no natural or accomplished position): rejected,
  because every player needs at least one real position.
- Club with fewer than 11 players or no goalkeeper: loads with a warning ("not playable"). The
  sample world MUST NOT contain such clubs.
- Date of birth that gives an age outside 14–45 at the dataset's reference date: rejected.
- Hidden attributes missing (public sources never provide them): allowed. Documented neutral
  defaults are used and the record is marked "hidden attributes defaulted" in its provenance.
- Text with accents and special characters (São João del-Rei, Uberlândia, Ipatinga): preserved
  exactly through import, export and display.
- Unknown extra fields in an import: ignored with a warning (forward compatibility), never a
  silent failure.

## Requirements *(mandatory)*

### Functional Requirements

**Clubs**

- **FR-001**: The system MUST represent a club with: a unique identifier, full name, short name,
  a 3-letter abbreviation, city, state (UF), country, primary and secondary colours, a home
  stadium (name, capacity), founding year and a reputation level (1–20).
- **FR-002**: A club MAY carry external references (source name + source identifier) so that
  later re-imports can match it to the same club.

**Players: identity and physical profile**

- **FR-003**: The system MUST represent a player with: a unique identifier, full name, display
  name (as known in football, e.g. "Hulk"), date of birth, one or more nationalities, height
  (cm), weight (kg), and left-foot and right-foot ability (each 1–20, as in FM, so that "either
  foot" is expressible).
- **FR-004**: Age MUST be derived from date of birth and a reference date (the game date). It is
  never stored independently.
- **FR-005**: A player MAY carry external references, like clubs (FR-002).

**Players: attributes (FM benchmark)**

- **FR-006**: Every player MUST have the full FM visible attribute set as integers from 1 to 20:
  - **Technical (14)**: corners, crossing, dribbling, finishing, first touch, free-kick taking,
    heading, long shots, long throws, marking, passing, penalty taking, tackling, technique.
  - **Mental (14)**: aggression, anticipation, bravery, composure, concentration, decisions,
    determination, flair, leadership, off the ball, positioning, teamwork, vision, work rate.
  - **Physical (8)**: acceleration, agility, balance, jumping reach, natural fitness, pace,
    stamina, strength.
  - **Goalkeeping (11)**: aerial reach, command of area, communication, eccentricity, handling,
    kicking, one on ones, punching (tendency), reflexes, rushing out (tendency), throwing.
- **FR-007**: All players store all attribute groups (outfield players have low goalkeeping
  values and vice versa). The display hides the irrelevant group, as FM does.
- **FR-008**: Every player MUST have the FM hidden attributes, as integers from 1 to 20:
  adaptability, ambition, consistency, controversy, dirtiness, important matches, injury
  proneness, loyalty, pressure, professionalism, sportsmanship, temperament, versatility.
  When the source lacks them, documented neutral defaults apply (see Edge Cases).
- **FR-009**: Every player MUST store a hidden Potential Ability (PA, 1–200, FM scale), so the
  data format does not change when player development arrives in v1. PA MUST be at least the
  player's Current Ability. Current Ability (CA, 1–200) is never stored. It is derived from the
  player's attributes at his best position, so it can never contradict them. The derivation MUST
  be documented and monotonic (raising a key attribute never lowers CA). If a source provides no
  PA, it defaults to the derived CA and the record is marked "potential defaulted" in provenance.

**Positions**

- **FR-010**: The system MUST use FM's 14 position codes: GK, DL, DC, DR, WBL, WBR, DM, ML, MC,
  MR, AML, AMC, AMR, ST. Each player has a familiarity (1–20) for each position. Unlisted
  positions default to 1.
- **FR-011**: Familiarity MUST be shown using FM's bands: Natural (18–20), Accomplished
  (15–17), Competent (12–14), Unconvincing (9–11), Awkward (5–8), Ineffectual (1–4).
- **FR-012**: The system MUST compute a position-suitability rating for any player at any
  position. It combines the attributes FM considers key for that position with the player's
  familiarity, and lower familiarity reduces it. The attribute weights per position MUST be
  documented and testable.
- **FR-013**: The system MUST rank a squad by suitability for a given position, and suggest the
  best XI for a given list of 11 positions as an optimal assignment (each player used at most
  once, maximum total suitability).
- **FR-014**: The system MUST provide a basic catalogue of 5 standard formations (4-4-2, 4-3-3,
  4-2-3-1, 3-5-2, 5-3-2), each a named list of 11 slots (exactly one GK), so spec 005 can offer
  formation choice and FR-013 can suggest a best XI for it. A formation is data, not hard-coded
  logic, so later specs can add user-created formations, separate in-possession and
  out-of-possession shapes, and free placement of a player anywhere on the pitch (see
  Assumptions). Roles, duties and instructions are spec 006.

**Squad membership**

- **FR-015**: A player belongs to at most one club at a time, or none (free agent).
- **FR-016**: Squad membership MUST include an optional shirt number (1–99, unique per club) and
  MAY include these optional fields, which are kept for later specs and real-data imports: market
  value, wage, contract expiry date. No contract rules (renewals, clauses, loans) are in scope.

**Data import format and provenance**

- **FR-017**: The system MUST define a documented, versioned, human-editable data format for
  clubs, players (identity, attributes, positions) and squad membership. The format MUST be
  editable by the owner without programming tools. It is a set of spreadsheet-compatible
  plain-text tables, one table per file (clubs, players, attributes, positions, memberships,
  provenance). They open directly in Excel, and version control shows readable line-level diffs.
  UTF-8 with accents preserved, and a file must survive a save from Excel without breaking.
- **FR-018**: Every dataset MUST include a provenance record: source name(s), retrieval date,
  transformation/tool version, the reference date of the data, a free-text notes field and
  whether the data is fictional or real. Import MUST refuse datasets without provenance.
- **FR-019**: Import MUST validate everything before loading anything (all-or-nothing). It
  MUST report all errors in one pass, each with file, record identifier, field, the offending
  value and the rule broken.
- **FR-020**: Import MUST distinguish errors (block the import) from warnings (implausible but
  allowed values, unknown fields, unplayable clubs). Warnings are listed for human review.
- **FR-021**: The system MUST export any loaded dataset to the same format so that export →
  import is lossless (identical data, provenance included).
- **FR-022**: The format MUST carry a format version. Importing an older supported version MUST
  work. Importing an unknown newer version MUST fail with a clear message.
- **FR-023**: This spec MUST NOT include any conversion from external sources (SoFIFA,
  Transfermarkt). That is spec 011.

**Fictional sample dataset**

- **FR-024**: The repository MUST include a fictional sample world of 12 clubs. They use
  fictional names styled after Minas Gerais football (no real club names, badges or real
  people), in tiers: 3 strong, 5 mid, 4 small.
- **FR-025**: Every sample club MUST have a playable squad of 25–30 players, including at least
  3 goalkeepers and at least 2 natural players for each line (defence, midfield, attack). Ages
  follow a realistic professional distribution (roughly 17–37).
- **FR-026**: Sample players MUST be coherent with their positions: a player's key attributes
  for his natural position are, on average, higher than his other attributes. Hidden attributes
  vary realistically, not all at a single value.
- **FR-027**: The sample world MUST be produced by a deterministic generator (same version + seed
  → identical output) and committed in the import format, with provenance marking it fictional
  and naming the generator version and seed.
- **FR-028**: The sample world MUST pass import validation with zero errors and zero
  "not playable" warnings.

### Key Entities

- **Club**: an organisation with identity (names, abbreviation, colours, location), a home
  stadium, a reputation level and external references. Has a squad.
- **Player**: a person with identity (names, birth date, nationalities, physical profile, feet),
  the full FM attribute set (visible and hidden), position familiarities and external references.
- **Squad Membership**: links a player to a club, with an optional shirt number and optional
  commercial fields (market value, wage, contract expiry).
- **Position**: one of FM's 14 codes. Used for familiarity, suitability and lineups.
- **Dataset**: a self-contained collection of clubs, players and memberships, with a format
  version and a reference date.
- **Provenance Record**: where a dataset came from, when, through which tool version, whether it
  is fictional, and which records had defaulted values or manual edits.
- **Validation Report**: the result of an import, with errors (blocking) and warnings (review),
  each located precisely.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The sample world (12 clubs, about 330 players) loads and validates in under
  2 seconds on the reference PC.
- **SC-002**: Regenerating the sample world with the same generator version and seed produces
  an identical dataset 100% of the time.
- **SC-003**: Export followed by re-import is lossless for 100% of records and fields in the
  sample world.
- **SC-004**: For each of at least 15 distinct deliberately-broken fixtures (one per validation
  rule), the import is rejected and the report pinpoints the exact file, record and field.
- **SC-005**: In the sample world, for every position, the average of that position's key
  attributes among natural players exceeds the average among other outfield players by at least
  2 points. Goalkeepers' average goalkeeping attributes exceed outfield players' by at least 8.
- **SC-006**: On hand-built fixtures, the suggested best XI matches the known optimal assignment
  in 100% of cases.
- **SC-007**: The owner can find who can play a given position and see the ranked list in one
  command, with no manual calculation.
- **SC-008**: The owner can correct a data error by editing the exported files without
  programming tools and re-import it in under 5 minutes.

## Assumptions

- **Scope boundaries**: competitions, calendar and Mineiro participants (002), match simulation
  (003/007), saves (004), roles, duties and instructions (006), and conversion from real sources
  (011) are out of scope. Contracts, transfers, finances, morale, injuries status and player
  development are v1 and out of scope, apart from the optional fields in FR-016.
- **Sample clubs are fictional**: 12 clubs, consistent with the Campeonato Mineiro's recent
  12-team format. The actual competition format is defined in spec 002.
- **Neutral defaults** for missing hidden attributes are 10, except dirtiness and injury
  proneness (8) and controversy (6), documented with the format.
- **Attribute weights per position** for suitability follow FM's published "key attributes"
  per position/role as closely as public information allows. Exact weights are tuned in later
  specs; this spec only requires that they are documented and tested.
- **Staff, referees and national teams** are separate entities in later specs.
- **Formation evolution** (owner's direction): the catalogue in FR-014 is a starting point.
  Later specs (006 or after) will add custom formations, distinct attacking and defending shapes,
  and free placement of players anywhere on the pitch. This spec only ensures formations are
  data-driven so that work needs no model rewrite.
- **Single user and offline**: no multi-user or online concerns for this spec.
