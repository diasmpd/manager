# Feature Specification: Quick Sim

**Feature Branch**: `003-quick-sim`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "003 Quick sim: a fast statistical match simulator (the "world" tier of the two-tier engine) that replaces 002's placeholder ResultProvider. Produces full-time scorelines plus a per-match stat line (shots, shots on target, xG, possession, corners, fouls, yellow/red cards, goal scorers and minutes, assisters) from the two clubs' squads: picks each side's XI with 001's best-XI, derives attack/midfield/defence/goalkeeping strengths from FM attributes, applies home advantage, and simulates in minute- or phase-level chunks so that game state (score, minute, red cards) changes behaviour. Deterministic per match seed. Calibrated against real league targets (Brasileirão Série A and state championships averages for goals per match, home/draw/away split, shots, xG, cards, red cards, score distribution, upsets by strength gap), with a calibration harness (PR gate ~200 matches / 2 seasons, milestone gate ≥1,000 matches) that prints before/after metrics with tolerance bands and sources. Cards feed 002's card tiebreakers. Penalty shootouts use the takers' and keeper's attributes. Must stay within the constitution's budget (full world matchday ≤5 s; a Mineiro matchday is 6 matches). No tactics yet (spec 006): each side uses its default formation; tactical exploit check is deferred and stated. Milestone 0."

**Milestone**: 0 (Prototype: Campeonato Mineiro). **Benchmark**: Football Manager's background
("quick") match results and match stats. FM plays unwatched matches with its full engine at
reduced detail. This project instead uses a separate statistical sim for the world tier
(Constitution, Technical Constraints: two-tier engine), so the world can be simulated before the
positional engine (spec 007) exists. The two are cross-validated once both exist.

**Real-world reference** (retrieved 2026-10-02; details in [Calibration targets](#calibration-targets)):
- Brasileirão Série A 2024 and 2025 results, from the Wikipedia season pages, whose results
  matrices cite the CBF
  ([2025](https://en.wikipedia.org/wiki/2025_Campeonato_Brasileiro_S%C3%A9rie_A),
  [2024](https://en.wikipedia.org/wiki/2024_Campeonato_Brasileiro_S%C3%A9rie_A)). The
  per-match counts were made by this project from those matrices: 720 of 760 matches parsed.
- Série A 2025 cards: [Itatiaia](https://www.itatiaia.com.br/esportes/futebol/futebol-nacional/brasileirao-serie-a/saiba-qual-foi-o-time-com-mais-expulsoes-no-brasileirao-2025/)
  (95 red cards in 380 matches) and
  [Gazeta Mercantil](https://gazetamercantil.com/estatisticas-de-brasileirao-serie-a-2025)
  (903 yellow cards in the first 173 matches).
- Shots on target and corners, Série A 2025:
  [Grêmio News, shots](https://www.gremionews.com.br/media-de-chutes-a-gol-no-brasileirao-2025-confira-os-principais-indices-dos-times-e-jogadores),
  [Grêmio News, corners](https://www.gremionews.com.br/geral/2600-escanteios-brasileirao-2025-media-total-times).
- Campeonato Mineiro first phase 2025 and 2026, from the group tables on the Wikipedia season pages
  ([2026](https://en.wikipedia.org/wiki/2026_Campeonato_Mineiro),
  [2025](https://en.wikipedia.org/wiki/2025_Campeonato_Mineiro)): 96 matches.

## User Scenarios & Testing *(mandatory)*

The single user is the owner. Until the terminal game (spec 005), every scenario is exercised
through the core's command-line interface (Constitution III).

### User Story 1 - Believable results for every match (Priority: P1)

The owner plays a Mineiro season (spec 002), and every result now comes from the quick sim, not
the placeholder. Scorelines look like real Brazilian football: mostly 1–0, 1–1 and 2–1 results,
about a quarter of matches drawn, home sides winning about half the time, strong clubs usually
beating weak ones but not always. The "(provisório)" mark disappears from the views.

**Why this priority**: it is the reason the spec exists. Every later system (tables, the career
loop, the terminal game) needs results that feel real.

**Independent Test**: play a season with the quick sim and read the tables and results. Then run
the calibration harness and check the scoreline metrics against the real-data bands.

**Acceptance Scenarios**:

1. **Given** a started Mineiro season, **When** the owner plays it to the end, **Then** every match
   has a quick-sim result, the season completes with valid outcomes, and no result is marked
   provisional.
2. **Given** the calibration harness, **When** it runs its PR-gate sample, **Then** goals per match,
   the home/draw/away split, the share of 0–0 draws, the total-goals distribution and favourite
   win rates are all inside their tolerance bands.
3. **Given** the same match seed, **When** a match is simulated twice, **Then** the result and every
   stat are identical. A different seed can give a different result.

---

### User Story 2 - A match report line for every match (Priority: P2)

For any played match the owner sees a short stat line, as in FM's results screens: shots, shots on
target, xG, possession, corners, fouls, yellow and red cards per side, plus the goal scorers with
minutes (and assisters) and the players booked or sent off.

**Why this priority**: the stats make results believable and debuggable. Cards feed 002's card
tiebreakers. Scorers are the first player-level output, the basis for top-scorer lists and, later,
for player ratings (spec 008).

**Independent Test**: show one match's report from the CLI. Check that the stat line is
consistent (goals ≤ shots on target ≤ shots, scorers belong to the side that scored, minutes in
1–90+stoppage) and that card totals feed the tables.

**Acceptance Scenarios**:

1. **Given** a played match, **When** the owner opens its report, **Then** both sides show shots, shots
   on target, xG, possession (summing to 100%), corners, fouls, yellow cards and red cards.
2. **Given** a match with goals, **When** the report is shown, **Then** every goal lists the scorer,
   the minute and the assister if any. Scorers are players in that side's match squad who were on
   the pitch at that minute.
3. **Given** a season played with the quick sim, **When** two clubs are level on every criterion
   before the card criteria, **Then** the table separates them by fewer red, then fewer yellow
   cards (002 FR-012) instead of falling through to lots.
4. **Given** a played season, **When** the owner lists the top scorers, **Then** the list is ordered by
   goals and shows each player's club.

---

### User Story 3 - Game state changes the match (Priority: P3)

Inside a match, what has happened changes what happens next, as in real football:
- a team that is behind pushes forward late, creating more chances and leaving more space behind;
- a team that is ahead late protects the lead;
- a sent-off player weakens his side for the rest of the match;
- a booked player eases off his tackles to avoid a second yellow. This is the owner's
  Brasileirinho pain point (roadmap pain-point log), and it carries a trade-off: he wins fewer
  duels, so his side defends a little worse.

**Why this priority**: it is the difference between a dice roll and a match. It is what makes
late equalisers, comebacks and the "booked player" behaviour exist before the positional engine
(spec 007).

**Independent Test**: run the harness and compare matches by game state: goals by 15-minute
period, the scoring rate of a trailing side after minute 75 versus its pre-match rate, the
strength drop after a red card, and the second-yellow rate of booked players with and without
the caution behaviour.

**Acceptance Scenarios**:

1. **Given** many simulated matches, **When** goals are counted by 15-minute period, **Then** the last
   period (76–90+) has the most goals and the first period (1–15) the fewest.
2. **Given** matches where a side is behind after minute 75, **When** its chance rate is compared
   with its rate in level games, **Then** it is higher, and so is the rate it concedes.
3. **Given** matches with a red card, **When** the shorthanded side's result is compared with
   matches of the same strength gap without one, **Then** its points per match are lower.
4. **Given** booked players, **When** the caution behaviour is on, **Then** their second-yellow rate
   is lower than with the behaviour off, and their side concedes slightly more. Both effects are
   reported by the harness (Constitution V: no free bonus).

---

### User Story 4 - Penalty shootouts decided by the players (Priority: P4)

When a knockout tie goes to penalties (002 FR-017), the shootout is played kick by kick by the
players on the pitch at the end of the match. The best penalty takers kick first, and the
goalkeeper's attributes matter.

**Why this priority**: 002 already runs shootouts with a fixed 75% conversion. This makes them
depend on the squads, but they are rare (a few per season).

**Independent Test**: simulate many shootouts with hand-built squads. Overall conversion is near
the real rate, better takers convert more often, and a better keeper saves more.

**Acceptance Scenarios**:

1. **Given** a tie level after the last leg, **When** the shootout is played, **Then** the takers are
   players on the pitch at the final whistle, ordered by penalty-taking ability, and the order
   repeats after every player has taken one (sent-off players excluded).
2. **Given** thousands of simulated kicks, **When** conversion is measured, **Then** it is within the
   tolerance band, and takers in the top quartile of penalty ability convert more often than
   those in the bottom quartile.

---

### User Story 5 - The owner runs the calibration (Priority: P5)

The owner (or CI) runs one command that simulates a fixed calibration sample and prints, for every
metric: the simulated value, the real target, the tolerance band, pass/fail, and the source with
its retrieval date. A second, larger "milestone" run uses at least 1,000 matches. The report also
records the core and Python versions (Constitution II).

**Why this priority**: the constitution makes it a gate (Principle I). It is listed last because
stories 1–4 are measured with it, so it is built first in the plan.

**Independent Test**: run the PR gate twice: the reports are identical. Change a model constant
on purpose so that goals per match leave their band, and the gate fails with the metric named.

**Acceptance Scenarios**:

1. **Given** the PR gate, **When** it runs on the reference PC, **Then** it finishes in under 30
   seconds and prints every metric with value, target, band, verdict and source.
2. **Given** a metric outside its band, **When** the gate runs, **Then** it exits with a failure
   and names the metric.
3. **Given** a previous report, **When** the gate runs, **Then** the report shows before/after values
   so a PR can include them (Constitution, Development Workflow).

### Edge Cases

- A club with fewer than 11 fit players, or no goalkeeper in its squad: the XI is completed
  (an outfield player in goal, with a heavy penalty) and the match is still played. The match
  report notes it.
- Two red cards to the same side: the side plays with 9. A side reduced below 7 players
  (abandoned in the real Laws) does not occur in practice. The sim caps a side at 3 red cards
  per match.
- A goal in stoppage time is shown as 90+N (or 45+N), never as minute 93.
- A shootout that reaches every outfield player: the order restarts (Laws of the Game), and only
  the players on the pitch at the end take part.
- The same match simulated in a different order, or alone instead of within the season, gives the
  same result (per-match seed, 002 R4).
- Extreme mismatches (best club v worst club) still allow upsets, at a rate within the favourite
  band.
- Own goals: about 3% of goals, credited to the scoring side with no scorer from it. The report
  shows "(contra)".

## Requirements *(mandatory)*

### Functional Requirements

**Integration with 002**

- **FR-001**: The quick sim MUST provide results through 002's result-provider replacement point,
  and MUST become the default provider of a new season. The placeholder stays available only
  for 002's own tests.
- **FR-002**: Results MUST be deterministic per match: the same season seed and match id give
  the same result and stats, independent of play order (Constitution II, 002 R4).
- **FR-003**: Each result MUST carry `source = quick_sim`, and the views MUST stop marking these
  results as provisional.
- **FR-004**: Card counts per side MUST be recorded on each result so that 002's card tiebreakers
  use them.

**Team strength**

- **FR-005**: Each side's XI MUST be picked with 001's best-XI for the club's default formation.
  A bench of up to 9 players is picked from the rest of the squad, covering a goalkeeper when one
  exists.
- **FR-006**: Team ratings (attack, midfield/control, defence, goalkeeping, set pieces, discipline)
  MUST be derived from the attributes of the players on the pitch, weighted by their positions,
  and recomputed when the players on the pitch change (substitution, red card).
- **FR-007**: Home advantage MUST be applied, sized so the home/draw/away split matches the
  target. A neutral venue (the 002 final) MUST apply none.

**Match flow**

- **FR-008**: A match MUST be simulated in time slices of at most 5 minutes, plus first- and
  second-half stoppage time. In each slice, possession, chances and their quality (xG), shots,
  goals, fouls, cards and corners follow from the team ratings and the current game state.
- **FR-009**: Game state MUST change behaviour, as described in User Story 3:
  - a trailing side raises its attacking intent as time runs out, and concedes more;
  - a leading side protects a late lead;
  - a red card weakens the side for the rest of the match;
  - a booked player is more careful, with a measurable trade-off.
- **FR-010**: Each side MUST make up to 5 substitutions, in at most 3 windows plus half-time
  (current Laws), choosing players by position and fatigue proxy (minutes played) at typical
  real minutes. A substituted player cannot return. M0 has no player fatigue model; substitution
  timing follows a fixed distribution.
- **FR-011**: Every goal MUST have a scorer from the side on the pitch, chosen by a weighting of
  position and finishing-related attributes, and an assister in most goals (rate per target).
  Own goals and penalties are included at their target rates.
- **FR-012**: Cards MUST be given to players, weighted by position and their aggression- and
  tackling-related attributes. A second yellow MUST become a red. Direct reds are rarer than
  second yellows.

**Shootouts**

- **FR-013**: Penalty shootouts MUST follow the Laws: 5 kicks each, then sudden death. Only
  players on the pitch at the final whistle take part. The order is by penalty-taking ability
  and restarts after every eligible player has kicked. The probability of scoring depends on
  the taker's penalty-related attributes and composure and on the goalkeeper's attributes.

**Calibration (Constitution I)**

- **FR-014**: A calibration harness MUST simulate a fixed sample with fixed seeds and report each
  target metric: simulated value, target, tolerance band, verdict, source and retrieval date. It
  MUST also record the core version and Python version.
- **FR-015**: The PR gate MUST use at least 200 seasons' worth of Mineiro first-phase matches,
  or an equivalent fixed sample of at least 2 league seasons. The milestone gate MUST use at least
  1,000 matches. Both are deterministic: the same code gives the same report.
- **FR-016**: The harness MUST compare against a stored previous report and show before/after
  values.
- **FR-017**: Calibration targets and their sources MUST be stored as data in the public
  repository (aggregate statistics only, Constitution I and VI), not hard-coded in the harness.
- **FR-018**: Primary targets (gates) and secondary targets (reported with wider bands, warnings
  only until better-sourced) MUST be distinguished. A secondary target is promoted to a gate
  once it has a source as strong as the primary ones.

**Viewing**

- **FR-019**: The CLI MUST show:
  - a match report (stat line, goals with minutes and assisters, cards);
  - the top scorers of a season;
  - the calibration report.

  All output is in pt-BR.

**Out of scope (stated deviations)**

- **FR-020**: Tactics are not modelled. Each side uses its default formation and a neutral
  mentality. The tactical exploit check (Constitution I) is deferred to spec 006 and recorded
  there. Fatigue across matches, injuries, suspensions and morale are not modelled (the match
  records cards per player so suspensions can be built in 004/005).

### Key Entities

- **Team ratings**: attack, control, defence, goalkeeping, set pieces and discipline for one
  side at one moment of the match. Derived from the players on the pitch.
- **Match state**: minute, score, players on the pitch per side, cards per player, substitutions
  used, and accumulated stats.
- **Match event**: minute (with stoppage notation), side, kind (goal, own goal, penalty goal,
  shot, shot on target, yellow, second yellow, red, substitution, corner), players involved,
  and xG for shots.
- **Match report**: the full-time stat line per side, plus the ordered event list.
- **Calibration target**: metric id, description, target value, tolerance band, primary or
  secondary, source, retrieval date and the sample it applies to (league or state phase).
- **Calibration report**: per-metric results, versions, sample definition, seeds and verdict.

## Calibration targets

Sample: "Série A" means 2024 and 2025 combined (720 matches counted from the CBF results
matrices). "Mineiro" means the first phase of 2025 and 2026 (96 matches). Bands are a first
proposal for owner review. They reflect both the sample sizes and the season-to-season
variation seen in the data.

| Metric | Target | Band | Kind | Source |
|---|---|---|---|---|
| Goals per match | 2.50 | 2.30–2.70 | primary | Série A 2024 (2.45), 2025 (2.55) |
| Home win / draw / away win | 48.6% / 26.1% / 25.3% | ±4 pp each | primary | Série A 2024–25 |
| Home goals / away goals per match | 1.47 / 1.02 | ±0.15 each | primary | Série A 2024–25 |
| 0–0 share | 6.6% | 4.5–9% | primary | Série A 2024–25 |
| Total goals 0 / 1 / 2 / 3 / 4 / 5+ | 6.6 / 20.4 / 25.3 / 25.3 / 13.2 / 9.2 % | ±4 pp each | primary | Série A 2024–25 |
| Top-5 v bottom-5: favourite W / D / L | 65% / 24% / 11% | ±10 pp each | primary | Série A 2024–25 (100 matches; positions from the final table) |
| Yellow cards per match | 5.2 | 4.5–6.0 | primary | Série A 2025 (903 in 173 matches) |
| Red cards per match | 0.25 | 0.17–0.33 | primary | Série A 2025 (95 in 380) |
| Mineiro first-phase draw share | 29% | 22–36% | primary | Mineiro 2025–26 |
| Mineiro first-phase goals per match | 2.33 | 2.0–2.7 | primary | Mineiro 2025 (2.19), 2026 (2.48) |
| Shots on target per side | 4.2 | 3.5–5.0 | secondary | Série A 2025 club averages 3.5–5.5 |
| Shots per match (both sides) | 25 | 21–29 | secondary | provider figures 20–27; to be sourced in plan research |
| xG per match | ≈ goals per match | ±0.3 of simulated goals | secondary | definition (xG totals track goals over a season) |
| Corners per match | 9.8 | 8.5–11 | secondary | Série A 2025 club totals 8.8–11.0 |
| Fouls per match | 26 | 22–30 | secondary | provider figure 25.8 (2026); to be sourced |
| Goals by 15-minute period | last period highest, first lowest | shape | secondary | to be sourced in plan research |
| Shootout kick conversion | 75% | 70–80% | secondary | 002 placeholder value; to be sourced |
| Own goals share of goals | 3% | 1.5–4.5% | secondary | to be sourced |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the PR-gate sample, every primary target is inside its band.
- **SC-002**: On the milestone sample (≥ 1,000 matches), every primary target is inside its band,
  and every secondary target is reported.
- **SC-003**: The same seeds give byte-identical calibration reports, and any single match
  replayed alone gives the same result and stats as within its season.
- **SC-004**: Simulating a Mineiro matchday (6 matches) takes under 0.5 seconds, and a full
  Mineiro season with knockouts under 3 seconds, on the reference PC. A 10-match league matchday
  takes under 1 second, well inside the constitution's 5-second world matchday budget.
- **SC-005**: 100% of match reports are internally consistent:
  - goals ≤ shots on target ≤ shots;
  - possession sums to 100%;
  - every scorer, assister and booked player was on the pitch at that minute;
  - no player has more than 2 yellows or more than 1 red;
  - card totals equal the per-player cards.
- **SC-006**: With the caution behaviour on, booked players' second-yellow rate is at least 25%
  lower than with it off, and the harness shows the defensive cost.
- **SC-007**: Over 1,000 seasons, 002's season invariants still hold with the quick sim: every
  season completes with valid outcomes, and no card tiebreak falls through to lots because cards
  were missing.

## Assumptions

- **Calibration world**: the sample world's 12 clubs. For league-style metrics they play a
  double round-robin. The "top-5 v bottom-5" target is scaled to the sample: top 3 v bottom 3 of
  12, which is the same share of the table. The sample world's strength spread may differ from
  the real Série A. If favourite rates cannot meet the band without distorting other targets,
  the sample generator's spread is adjusted (a 001 data change), not the sim.
- Série A is the primary reference because it has the larger and better-documented sample.
  State championships (Mineiro) have more draws and fewer goals, and the 96-match Mineiro sample
  is used as a looser check. M0 plays the Mineiro, so both are gates. One model must pass both;
  if it cannot, the owner decides which wins.
- Without tactics (spec 006), both sides use a neutral approach, so the effect of style on
  shots, possession and fouls is not modelled. This is why those targets are secondary.
- Real cards are spread over the whole squad, including the bench and staff. The sim gives cards
  only to players on the pitch, so the target counts player cards on the pitch. Staff cards are
  ignored: they are rare in the counts used.
- Shootouts reuse the Laws as of 2026 (ABAB order). No ABBA.
- "Fatigue" for substitutions is a minute-based proxy. The real fatigue model belongs to the
  positional engine (007) and the career loop (004).
- Performance is measured on this Windows PC (the reference PC of the constitution), as in 002.

## Owner review points

These are not blockers. Defaults are in the spec, and they are listed so the owner can change them
at review:
1. **The bands** in the calibration table (for example ±4 pp on home/draw/away).
2. **Mineiro vs. Série A when they disagree**: the default is that both are gates.
3. **The caution behaviour** in the quick sim. The default is on: the quick sim shows the effect
   of the owner's pain-point fix even before the positional engine.
