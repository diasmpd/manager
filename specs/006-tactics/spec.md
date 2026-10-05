# Feature Specification: Tactics

**Feature Branch**: `006-tactics`

**Created**: 2026-10-03

**Status**: Draft

**Input**: Roadmap 006, "Tactics model: roles and duties, team and individual instructions, set
pieces", split by the owner into 006 (tactics model) and 006b (formation editor with free
placement, alongside the positional engine 007). The owner's decisions were taken on 2026-10-03
as multiple-choice questions.

**Milestone**: 0. **Benchmark**: **Football Manager 26**. Its tactics model replaced duties
with separate In-Possession (IP) and Out-of-Possession (OOP) roles, uses separate IP and OOP
formations, and groups team instructions by phase of play. The owner asked to "follow
everything FM26 makes right".

## Owner decisions

1. **Split**: this spec is the tactics model. Formation editing, free player placement and
   custom shapes are 006b, which comes with the positional engine (007).
2. **Depth**: FM's full option set, not a subset.
3. **Model**: FM26.
   - Every player in the XI has an IP role and an OOP role. There are no duties.
   - The team has an IP formation and an OOP formation, both from the catalogue.
   - Team instructions are organised by phase.
4. **Mentality**: real, with 7 levels (Very Defensive, Defensive, Cautious, Balanced,
   Positive, Attacking, Very Attacking) that genuinely change risk, tempo and positioning.
   FM26 still shows a mentality whose effect players dispute. Ours works.
5. **Effect before the positional engine**: tactics act through the quick sim (003). Every
   option has measured effects with trade-offs. Calibration must still pass, and an exploit
   check must show that no tactic dominates (Constitution I).
6. **Opponents**: each AI club has a tactical style (from its squad and manager profile) and
   adapts it to the opponent and the match state, FM-style.

## The FM26 option set (reference)

Names are FM26's. In-game they appear in pt-BR. Sources: FM26 feature page and the FMScout and
FM Sidekick role databases, retrieved 2026-10-03 (see research).

**Team instructions — in possession**

| Phase | Instructions and settings |
|---|---|
| Overview | Passing directness (5 steps); Tempo (Lower / Standard / Higher); Time wasting (Less / Standard / More); Attacking transition (Counter / Standard / Patient build-up); Attacking width (5 steps); Creative freedom (Disciplined / Balanced / Expressive); Play for set pieces (Keep ball in play / Standard) |
| Build-up | Build-up strategy (Play through press / Mixed / Direct); Goal kicks (Short / Mixed / Long); GK distribution speed (Slower / Balanced / Faster); GK distribution target (Centre-backs / Full-backs / Midfielders / Forwards) |
| Progression | Pass reception (Balanced / Overlapped); Dribbling (Reduced / Balanced / Encouraged); Supporting runs (Both flanks / One flank / Balanced); Progress through (Left / Balanced / Right) |
| Final third | Dribbling; Pass reception; Patience (Work ball into box / Balanced / Less often); Shots from distance (Reduced / Balanced / Encouraged); Crossing style (Low / Balanced / High) |

**Team instructions — out of possession**

| Phase | Instructions and settings |
|---|---|
| Overview | Line of engagement (High press / Mid block / Low block); Defensive line (Deeper / Standard / Higher / Much higher); Defensive line behaviour (Balanced / Offside trap / Step up); Trigger press (Less / Balanced / More); Defensive transition (Counter-press / Standard / Regroup); Tackling (Ease off / Standard / Aggressive) |
| High press | Pressing trap (Balanced / Active); Prevent short GK distribution (Yes / No) |
| Mid block | Pressing trap; Cross engagement (Hold position / Balanced / Contest) |
| Low block | Pressing trap; Cross engagement |

**Roles** (IP / OOP), by position:

| Position | In-possession roles | Out-of-possession roles |
|---|---|---|
| GK | Goalkeeper, Ball-Playing GK, No-Nonsense GK | Goalkeeper, Line-Holding Keeper, Sweeper Keeper |
| D C | Centre-Back, Ball-Playing CB, No-Nonsense CB, Advanced CB | Centre-Back, Covering CB, Stopping CB |
| D L/R | Full-Back, Inside Full-Back, Playmaking Wing-Back | Full-Back, Holding Full-Back, Pressing Full-Back |
| WB L/R | Wing-Back, Advanced WB, Inside WB, Playmaking WB | Wing-Back, Holding WB, Pressing WB |
| DM | Defensive Midfielder, Deep-Lying Playmaker, Half Back, Box-to-Box Midfielder, Box-to-Box Playmaker | Defensive Midfielder, Dropping DM, Screening DM, Wide Covering DM |
| M C | Central Midfielder, Midfield Playmaker, Wide Central Midfielder | Central Midfielder, Pressing CM, Screening CM, Wide Covering CM |
| M L/R | Wide Midfielder | Wide Midfielder, Tracking WM, Wide Outlet WM |
| AM C | Attacking Midfielder, Advanced Playmaker, Channel Midfielder, Free Role, Second Striker | Attacking Midfielder, Tracking AM, Central Outlet AM, Splitting Outlet AM |
| AM L/R | Winger, Inside Winger, Inside Forward, Wide Forward, Playmaking Winger | Winger, Tracking Winger, Wide Outlet Winger, Inside Outlet Winger |
| ST | Centre Forward, Channel Forward, Deep-Lying Forward, False Nine, Poacher, Target Forward | Centre Forward, Tracking CF, Central Outlet CF, Splitting Outlet CF |

**Individual player instructions**: FM's per-player overrides on top of the role (e.g. shoot
more or less often, dribble more or less, cross more or less often, close down more or less,
mark tighter, take more risks). The plan lists the full set, with the instructions each role
locks.

**Set pieces**: takers (penalties, corners left and right, free kicks direct and indirect,
long throws, captain), plus attacking and defending corner and free-kick setups (near post /
far post / short / mixed; zonal / man / mixed marking).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set up the team's tactic (Priority: P1)

The owner builds his tactic in the terminal game. He chooses:
- an IP formation and the OOP formation from the catalogue (the game suggests three fitting
  OOP shapes, as FM26 does);
- the mentality;
- the team instructions by phase;
- each starter's IP and OOP role, plus individual instructions.

The assistant shows each player's familiarity with his role. The tactic is saved with the
career and used in his matches.

**Why this priority**: it is the decision layer FM is about. Without it, matches are the same
for everyone.

**Independent Test**:
- Build a tactic with non-default settings in every group.
- Save and load the career.
- Play a match: the report records the tactic used, and loading restores it exactly.

**Acceptance Scenarios**:

1. **Given** an IP formation, **When** the OOP formation is chosen, **Then** the game suggests three
   fitting OOP formations, and any catalogue formation can be chosen.
2. **Given** a slot, **When** roles are chosen, **Then** only roles valid for that slot's position
   are offered (IP and OOP separately), and an invalid role is refused with the reason.
3. **Given** an instruction a role locks, **When** the owner tries to set it for that player, **Then**
   it is shown as locked, as in FM.
4. **Given** a saved tactic, **When** the career is saved and loaded, **Then** the tactic is
   identical.

---

### User Story 2 - Tactics change matches believably (Priority: P2)

Every option has an effect in the quick sim, each with a trade-off. Some examples:
- **Attacking mentality**: more shots and more chances conceded.
- **High press**: more turnovers high up, more fouls and faster fatigue, more space behind.
- **Counter-attack**: fewer, higher-quality chances.
- **Time wasting**: slower play when ahead and more bookings.

Effects are sized so the calibration targets still pass with the default tactic. Changing
tactics moves the metrics in the direction real football does.

**Why this priority**: it is what makes tactics matter (Constitution I: "Tactics MUST matter
believably").

**Independent Test**: for every option, simulate a fixed sample with the option on and off
(the rest neutral). The direction of each documented effect holds, the trade-off is
measurable, and the size stays within its documented band.

**Acceptance Scenarios**:

1. **Given** the default tactic for every club, **When** the PR calibration gate runs, **Then** every
   target passes, as in 003.
2. **Given** an option, **When** its effect test runs, **Then** each documented direction holds
   with statistical confidence (fixed seeds, tolerance bands).

---

### User Story 3 - No tactic dominates (Priority: P3)

The exploit check simulates a grid of tactics against the AI styles. No tactic is best against
every style, and no tactic gains more than a bounded advantage over the neutral tactic on
average.

**Why this priority**: the constitution requires it ("no single tactic may dominate across
opponents"). Owner decision 5.

**Independent Test**: the harness's exploit report on the PR sample lists each tactic's points
per match against each opponent style. It flags dominance.

**Acceptance Scenarios**:

1. **Given** the exploit grid, **When** it runs, **Then** for every tactic there is at least one
   opponent style against which it does worse than the neutral tactic.
2. **Given** the exploit grid, **When** it runs, **Then** the best tactic's average advantage over
   neutral is at most 0.20 points per match (band to be confirmed in the plan, from real
   tactical-effect sizes).

---

### User Story 4 - Opponents have styles and adapt (Priority: P4)

Each AI club gets a style, derived from its squad (e.g. a strong technical midfield → possession;
quick forwards and a weak defence → counter-attack) and from a manager profile. Before a match
it adapts to the opponent: a big underdog away sits deeper. During the match it adapts to the
score: chasing late, it raises the mentality.

**Why this priority**: tactics only matter if opponents differ (FM-style AI).

**Independent Test**:
- Styles over the sample clubs are varied and plausible.
- The adaptation rules fire in the documented situations.
- A season's AI tactics are deterministic.

**Acceptance Scenarios**:

1. **Given** the sample world, **When** styles are assigned, **Then** at least three distinct styles
   appear among the 12 clubs, each explained by its squad.
2. **Given** a strong home side against a weak visitor, **When** the visitor picks its tactic, **Then**
   its mentality is at most Cautious and its line of engagement at most a mid block.

### Edge Cases

- **A formation whose slots no longer match** (e.g. the IP formation is changed): roles reset
  to the slot defaults, and the owner is told which ones changed.
- **A player in an unfamiliar role**: allowed. His effectiveness drops by his familiarity with
  the position (001) and his attribute fit for the role (shown as a role-suitability rating).
- **Set-piece takers**: a taker who is suspended or substituted is replaced by the next best
  in a fallback order.
- **Red cards**: the tactic keeps its shape with one player fewer. Automatic reshuffles are 009
  (assistant), and the quick sim already handles numbers.

## Requirements *(mandatory)*

### Functional Requirements

**Model**

- **FR-001**: A tactic MUST hold:
  - the IP formation and the OOP formation (from the catalogue, which gains the common OOP
    shapes);
  - the mentality (7 levels);
  - every team instruction of the reference set, with its settings and defaults;
  - per slot, an IP role, an OOP role and individual instructions;
  - set-piece takers and setups.
- **FR-002**: Roles, the instructions each role locks, the role-to-position validity and the
  role attribute weights (role suitability) MUST be reference data (TOML), not code.
- **FR-003**: Validation MUST reject:
  - an unknown option;
  - a role invalid for its slot;
  - an individual instruction locked by the role;
  - an invalid set-piece taker.

  Each refusal gives a code and the path.
- **FR-004**: The user's tactic MUST be saved with the career (save format v3, with a migration).
  Every match report MUST record both sides' tactics.

**Effects (quick sim)**

- **FR-005**: The quick sim MUST read both sides' tactics. Each option changes documented
  model inputs, with trade-offs:
  - shot rate and chance quality;
  - shot rate and quality conceded;
  - possession;
  - fouls and cards;
  - fatigue proxy and substitution timing;
  - set-piece share;
  - counter-attack chances;
  - offside;
  - goalkeeper distribution risk.

  The size of every effect is a parameter in `model.toml`.
- **FR-006**: Role suitability (attributes against the role's key attributes) MUST change the
  player's contribution to the team ratings, as position familiarity does today.
- **FR-007**: With every club on the default tactic, the calibration gates (003) MUST pass
  unchanged.
- **FR-008**: An option-effects test MUST verify the direction and the band of every documented
  effect, and an exploit check MUST run in the PR gate (US3).

**AI**

- **FR-009**: Each AI club MUST have a style (a full tactic), derived deterministically from its
  squad and a manager profile, adapted per match (opponent strength, venue, importance) and in
  the match (score and minute). The rules are data.

**UI**

- **FR-010**: The terminal game MUST gain a Tactics screen:
  - formations with the three OOP suggestions;
  - the mentality;
  - instructions grouped by phase;
  - roles per player, showing suitability;
  - individual instructions, with locked ones marked;
  - set pieces.

  The rules stay in the facade (Constitution III).

## Success Criteria *(mandatory)*

- **SC-001**: With default tactics, both calibration gates pass.
- **SC-002**: Every option has at least one documented effect and one trade-off, each verified
  by a test.
- **SC-003**: Exploit check: no tactic is best against every AI style, and the maximum average
  gain over neutral is ≤ 0.20 points per match on the PR sample.
- **SC-004**: A full season with tactics still plays in under 3 s (003's SC-004).
- **SC-005**: Save and load restores tactics exactly. Every report records both tactics.

## Assumptions

- **Effect sizes** come from published tactical analytics where they exist (e.g. the effect of
  pressing intensity on turnovers and fouls, of possession style on shots). Otherwise they are
  bounded estimates, marked as such in `model.toml` and refined with the positional engine.
- **OOP roles follow the IP slot (owner decision, M0 simplification)**: an OOP role is
  validated against the slot's IP position, so the OOP formation does not change which OOP roles
  are allowed (in FM26 a 4-3-3 winger defends as a wide midfielder in a 4-1-4-1). Mapping IP slots
  to OOP-formation positions, and giving the OOP shape its own lever effects, is deferred (see the
  roadmap). It needs an IP-to-OOP slot mapping, which is a design task of its own.
- **Formation change (owner decision, second review)**: when the selection's formation changes,
  each slot keeps its roles and player instructions if the new formation has a slot at the
  same position and the roles are still valid there; the other slots get default roles. The
  owner is told which positions were reset. A saved tactic that is no longer valid with the
  current data falls back to the default tactic, with a notice.
- **Goal totals and game state (owner decision, T011)**: real goal totals are under-dispersed
  (fewer 0-0s and more 3-goal games than chance alone gives). The quick sim models two
  score-dependent behaviours: a goalless game opens up as it goes on, and a match with 3+ goals
  is managed by both sides. The league targets use the full 760-match count of Série A 2024–25
  (research R6).
- **Shapes before 007**: IP and OOP shapes, roles and positions act through ratings and rates.
  Real positioning arrives with the positional engine (007) and the formation editor (006b).
- **The OOP formation catalogue** adds FM's common shapes (4-1-4-1, 4-5-1, 4-4-1-1, 5-4-1,
  4-4-2 flat, 4-2-3-1 mid block and others) to the existing five formations.
- **Manager profiles** for AI clubs are generated (no staff model yet; staff is v1).
- **In-match changes** by the user (shouts, half-time talks, live tactic changes) are not in this
  spec. They belong with match-day interaction (later), and the AI's automatic in-match
  adaptation is included.
