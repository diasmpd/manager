# Research: Quick Sim (003)

Phase 0 decisions. Each entry: Decision / Rationale / Alternatives considered.

## R1. Model family: a minute-by-minute event model

- **Decision**: simulate each match minute by minute (45 + first-half stoppage, 45 + second-half
  stoppage). In each minute, each side has a small probability of:
  - a shot (with a sampled xG and an on-target flag);
  - a foul, which can lead to a card;
  - a corner;
  - a penalty.

  The probabilities come from the current team ratings (R2), home advantage, the time trend and
  the game state (R4). Goals are shots that beat the keeper (R3).
- **Rationale**: the spec needs per-minute events (scorers with minutes, cards per player,
  substitutions, game-state behaviour, red cards that change ratings). A scoreline-only model
  (Poisson or Dixon–Coles) cannot produce them. A minute is well within FR-008's 5-minute
  slices, and at about 200 random draws per minute-pair it costs about 1–2 ms per match in pure
  Python.
- **Alternatives**:
  - Bivariate Poisson / Dixon–Coles for the score, then decorating it with events afterwards.
    Calibrating scorelines is easy, but game state cannot affect the score, and a red card would
    be decorative. Rejected.
  - Possession-chain simulation (a mini positional model): duplicates spec 007 and is slower.
    Rejected.

## R2. Team ratings from FM attributes

- **Decision**: six composites per side, each on the 1–20 attribute scale, computed from the
  players **on the pitch**. Each player contributes attribute means weighted by his slot's line,
  scaled by his suitability for the slot (001's `suitability`).

| Composite | Attributes | Line weights (GK / DEF / MID / ATT) |
|---|---|---|
| attack | finishing, off_the_ball, composure, dribbling, first_touch, technique, anticipation, pace, acceleration | 0 / 0.15 / 0.5 / 1.0 |
| control | passing, vision, decisions, technique, first_touch, teamwork, work_rate, stamina | 0 / 0.4 / 1.0 / 0.4 |
| defence | marking, tackling, positioning, anticipation, concentration, heading, strength, jumping_reach, pace | 0 / 1.0 / 0.5 / 0.1 |
| goalkeeping | reflexes, handling, one_on_ones, aerial_reach, command_of_area, agility, concentration, positioning | GK only |
| set_pieces | corners, free_kick_taking, heading, jumping_reach | 0 / 0.5 / 0.5 / 0.5 |
| discipline (foul and card proneness) | aggression, dirtiness, inverted temperament, inverted tackling | 0 / 1.0 / 0.8 / 0.4 |

- A composite is the weighted sum over the players on the pitch divided by the weight of a full
  XI in the default formation, so a sent-off player lowers every line he contributed to (FR-006).
- **Rationale**: these mirror the attributes FM's own guides name per phase of play. Line weights
  stand in for roles until spec 006. Ratings are cheap: recomputed only when the players on the
  pitch change.
- **Alternatives**: use CA alone. One number cannot separate a good attack from a good defence,
  and a red card for a defender would cost the same as for a forward.

## R3. Chances, xG and goals

- **Decision**:
  - **Shot rate.** Per side per minute: `p_shot = base_shot · exp(β_att·(A − D_opp)/5 + β_ctl·(C − C_opp)/5) · home · trend(t) · state`,
    where A, D and C are the attack, defence and control composites.
  - **Shot quality.** Each shot draws an xG from a log-normal whose median rises with
    `(A − D_opp)`, clipped to 0.01–0.95.
  - **On target.** The chance the shot is on target is `0.25 + 0.9·xG`, capped at 0.95.
  - **Goal.** An on-target shot is a goal with probability
    `xG / p(on target) · keeper(G_opp)`, with `keeper = exp(−β_gk·(G_opp − 10)/5)`.

    So the expected goals of a shot equal its xG for an average keeper.
  - **Penalties.** A penalty arises from a small per-minute rate tied to attacking pressure. It
    has xG 0.78 and is converted by the taker against the keeper (R11).
  - **Own goals.** A fixed share of goals (target 3%) is converted into own goals at the moment
    a goal is scored. The scorer is then a defender of the conceding side.
- **Rationale**: tying goals to xG keeps the secondary target "xG ≈ goals" true by
  construction, so calibration only tunes shot volume and quality. A keeper factor lets the
  goalkeeping composite matter.
- **Alternatives**: a fixed conversion rate per shot. That gives no xG, and the keeper would
  not matter.

## R4. Game state and time

- **Decision**:
  - **Time trend.** It rises linearly from 0.85 at minute 1 to 1.15 at minute 90 and stays
    there in stoppage time (fatigue and open play).
  - **Trailing side.** From minute 60, its attacking intent rises by
    `δ_chase · min(deficit, 2) · (t − 60)/30`. Its shot rate goes up, and so does the quality
    of the counter-chances it concedes (`δ_exposed`).
  - **Leading side.** From minute 70, a side ahead by one goal lowers its own shot rate by
    `δ_protect` and the opponent's chance quality by `δ_protect/2`.
  - **Red card.** Ratings are recomputed without the player (R2), and the opponent's shot rate
    gains `δ_man_up`.
- **Rationale**: the spec requires that the last 15-minute period has the most goals (26.1% of
  Brasileirão 2025 goals came after minute 75, and 56% of Brasileirão 2019 goals came in the
  second half), and that comebacks and protecting leads both exist. Protecting a lead also
  pushes the draw rate up, toward the real 26–29%: plain Poisson models usually fall short of
  that.
- **Alternatives**: no game state, with Poisson draws inflated by a fixed factor (as in
  Dixon–Coles). It hits the draw rate without explaining it, and it cannot give late goals.

## R5. Fouls, cards and the caution behaviour

- **Decision**:
  - **Fouls.** Each side commits fouls at a per-minute rate scaled by its discipline composite
    and the opponent's attacking pressure (target 26 per match).
  - **Who fouls.** The fouler is drawn from the players on the pitch, weighted by line
    (DEF 1.0, MID 0.8, ATT 0.4, GK 0.05) × aggression × dirtiness.
  - **Cards.** A foul is a yellow with probability `y_base · f(aggression, dirtiness, temperament, minute)`.
    It is a direct red with a small fixed probability. A second yellow is a red.
  - **Caution behaviour** (Constitution V and the owner's pain point, on by default). A booked
    player's foul weight is multiplied by `κ_foul` (0.5) and his card-per-foul probability by
    `κ_card` (0.7). The trade-off: his side's defence composite loses `κ_cost` (15%) of his own
    defence contribution for the rest of the match.
  - **Harness switch.** The harness runs the PR sample with the behaviour on and off, and
    reports the second-yellow rate and the goals conceded by sides with a booked player
    (SC-006).
- **Rationale**:
  - Card targets: 5.2 yellows and 0.25 reds per match (Série A 2025).
  - Real data counts a second yellow as a yellow and a red. **Counting rule:** the yellow totals
    on a `Result` include both yellows of a sent-off player, and the red totals include the
    dismissal. 002's card tiebreakers read these totals.
- **Alternatives**: cards as a side-level Poisson count. Then players could not be suspended
  later, and the caution behaviour would be impossible.

## R6. Possession and corners

- **Decision**:
  - **Possession.** Home share is `50 + 50·tanh(γ·(C_home − C_away)/5 + home_poss)` in percent,
    rounded so the two sides sum to 100. A trailing side's late intent adds a little.
  - **Corners.** Per side per minute, the rate is proportional to that side's shot pressure
    (target 9.8 per match).
- **Rationale**: both are secondary targets until tactics exist (spec Assumptions).

## R7. Scorers, assists and substitutions

- **Decision**:
  - **Scorer.** Weight = line weight (ATT 1.0, AM 0.7, MID 0.35, DEF 0.12, GK 0) ×
    ((finishing + composure + off_the_ball)/3)².
  - **Headed and set-piece goals.** They use heading and jumping_reach instead, with DEF
    weight 0.4. This applies to 20% of non-penalty goals.
  - **Assists.** 75% of open-play goals have one. The assister is weighted by line (AM and
    wide players high) × (passing + vision + crossing)/3, and is never the scorer.
  - **Penalty taker.** The on-pitch player with the best penalty_taking (ties by composure,
    then id).
  - **Substitution windows.** Half-time (35% chance per side) and three windows drawn from
    55–65, 66–75 and 76–85, for 3–5 substitutions per side.
  - **Who goes off.** Weighted toward attacking players and low stamina, and toward attackers
    when chasing.
  - **Who comes on.** The bench player with the best suitability for the vacated slot.
  - **Booked players.** Weighted to come off (another FM-like assistant behaviour).
- **Bench.** The 9 best remaining players by CA, including a second goalkeeper if the squad
  has one.
- **Rationale**: FM's goal distribution has strikers well ahead, then attacking midfielders.
  Substitutions spread minutes and goals to bench players, which top-scorer lists and later
  ratings need.
- **Alternatives**: no substitutions in M0. Then every scorer would be a starter, and 005
  would need them anyway.

## R8. Stoppage time

- **Decision**: first half 1–5 minutes (uniform), second half 4–10 minutes (uniform). Events in
  stoppage time are stored as `(45, n)` or `(90, n)` and shown as "45+n" and "90+n".
- **Rationale**: the CBF applies extended added time. The values feed the time trend and late
  goals.

## R9. Parameters as data, fitted by a tuning tool

- **Decision**:
  - All model constants (base rates, β's, δ's, κ's, the home factor) live in
    `reference/quicksim/model.toml`, with a `model_version`.
  - A dev-only tool, `core/tools/tune_quicksim.py`, runs coordinate descent on a weighted
    squared distance to the primary targets over the PR sample, then writes the file.
  - The harness records the model version and a hash of the parameters in every report.
- **Rationale**: calibration changes should be data diffs, reviewable next to the before/after
  report. Determinism is unaffected, because the parameters are inputs.
- **Alternatives**: constants in code. That gives noisier diffs and no hash in reports.

## R10. Calibration samples and harness

- **Decision**:
  - **Targets** are stored in `reference/calibration/quicksim-targets.toml` (contracts), with
    their sources (FR-017).
  - **League sample.** The 12 sample clubs in a double round-robin (132 matches per season),
    built with 002's fixture generator (`all`, 2 rounds). Home/away, goals, cards, scorelines
    and top-3 v bottom-3 are measured on this sample.
  - **Mineiro sample.** Full 002 seasons. The first-phase draw share and goals per match are
    measured on it, and shootouts are counted.
  - **PR gate**: 20 league seasons (2,640 matches) + 50 Mineiro seasons (about 2,950 matches).
  - **Milestone gate**: 100 league seasons + 500 Mineiro seasons.
  - **Seeds** are fixed: `calibration:<sample>:<n>`.
  - **Report.** The harness writes a JSON report and prints a pt-BR table. With `--baseline`,
    it shows before/after values. The committed baseline is
    `core/calibration/quicksim-baseline.json`.
  - **Exit codes.** It exits 1 if any primary target is outside its band. Secondary targets
    only warn.
- **Rationale**:
  - The draw share's standard error at n = 2,640 is about 0.9 pp, well inside ±4 pp.
  - The sample is about 5,600 matches at about 2 ms each, plus lineups cached once (R12),
    which keeps the PR gate under 30 s.
- **Upsets target scaling**: the real target compares the top 5 v bottom 5 of 20 clubs (25% of
  the table at each end). The sample uses the top 3 v bottom 3 of 12, ranked by the final
  simulated table, which is the same method as the real target.

## R11. Shootouts

- **Decision**:
  - **Kick probability.** `p = clamp(0.752 + 0.012·(pen − 12) + 0.008·(composure − 12) − 0.010·(gk − 12), 0.55, 0.92)`,
    with `gk` the mean of reflexes, agility, one_on_ones and anticipation. This is refit by
    the tuning tool.
  - **Takers.** The players on the pitch at the final whistle (from the last leg's report),
    ordered by penalty_taking, then composure, then id. The order repeats after all eligible
    players have kicked.
- **Source**: 75.2% of 343 shootout kicks in major tournaments (PMC11627389, retrieved
  2026-10-02).
- **Protocol change**: `ResultProvider.shootout` gains a keyword `last_result: Result | None`.
  The provider reads the players on the pitch from it. The placeholder ignores it.

## R12. Performance: caching lineups

- **Decision**: 001's exact best XI costs about 0.11 s per club (measured on the sample). The
  provider caches the XI and bench per club id for its lifetime. Squads do not change in M0,
  and spec 004 will invalidate the cache on squad changes. The harness shares one provider
  across all its seasons.
- **Budget**:
  - A season is 12 lineups (about 1.4 s) plus 59 matches (about 0.1 s), inside SC-004's 3 s.
  - A matchday after the lineups are cached takes about 15 ms.

## R13. Integration with 002

- **Decisions**:
  - `Result` gains `report: MatchReport | None` (None for the placeholder).
  - `MatchContext` gains `neutral: bool`. `Season` sets it for `venue = "neutral"` stages, so no
    home advantage is applied (FR-007).
  - `start_season` defaults to `QuickSimProvider`. 002's tests that assert placeholder
    behaviour pass `result_provider=PlaceholderProvider(...)` explicitly.
  - Views mark "(provisório)" only when `source == "placeholder"` (already true in 002's CLI).
- **Card tiebreaks**: with the quick sim, every result has cards, so SC-007 checks that no
  table row is decided by lots because cards were missing.

## R14. Sources (retrieved 2026-10-02)

| Metric | Source |
|---|---|
| Goals, H/D/A, home/away goals, 0–0, total-goals distribution, favourites | Wikipedia season pages for Série A 2024 and 2025 (results matrices citing the CBF); counts by this project, 720 matches |
| Yellow / red cards | Gazeta Mercantil (903 yellows in 173 matches, Série A 2025); Itatiaia (95 reds, Série A 2025) |
| Mineiro draws and goals | Wikipedia, 2025 and 2026 Campeonato Mineiro group tables (96 matches) |
| Shots on target | Grêmio News, Série A 2025 club averages |
| Corners | Grêmio News, Série A 2025 club totals |
| Shots, fouls | FootyStats Série A 2026 (27.0 shots, 25.8 fouls per match), page cited by search, not directly retrievable (HTTP 403): secondary |
| Goals by period | Goal.com (26.1% of Brasileirão 2025 goals after minute 75); Revista Brasileira de Futsal e Futebol (Brasileirão 2019: 43.8% first half) |
| Shootout conversion | PMC11627389 (75.2% of 343 kicks) |
| Own goals | ExtraTime Premier League stats (2.9% in 2024–25, 3.9% in 2023–24); no Brazilian source found |
