# Research: Tactics (006)

Each entry: Decision / Rationale / Alternatives considered. Sources were retrieved 2026-10-03.

## R1. Benchmark: FM26's tactics model

- **Sources**:
  - the FM26 feature page "In Possession, Out of Possession: FM26's new tactical evolution"
    (footballmanager.com);
  - FMScout, "FM26 team instructions guide";
  - FM Sidekick role and player-instruction databases.
- **Facts used**:
  - duties are gone;
  - IP and OOP roles per position (about 70 in total);
  - an IP formation with three suggested OOP formations;
  - team instructions grouped by phase (IP: overview, build-up, progression, final third;
    OOP: overview, high press, mid block, low block);
  - 14 individual player instructions (10 IP, 4 OOP);
  - roles carry fewer hard-coded instructions than in FM24.
- **Mentality**: FM26 still displays it, and its effect is disputed in the community. Ours is a
  real 7-level setting (owner decision).

## R2. Effects through a small set of quick-sim levers

- **Decision**: every option maps to multipliers on a fixed set of per-side **levers** that
  the engine already understands, or gains:

| Lever | Engine meaning |
|---|---|
| `shot_rate` | own shot rate per minute |
| `chance_quality` | own xG median |
| `allow_rate` | opponent's shot rate (how much you allow) |
| `allow_quality` | opponent's xG median (space you leave) |
| `possession` | additive share of possession |
| `foul_rate` | own fouls |
| `card_rate` | own card probability per foul |
| `fatigue` | late-match penalty on own attack and defence (from minute 60) |
| `set_piece` | own corner and set-piece rate |
| `counter` | share of own shots that are counter chances (higher quality, from regains) |
| `error_risk` | own build-up errors: allowed high-quality chances |

- Effects are in **reference data** (`reference/tactics/effects.toml`): option → setting →
  {lever: multiplier}. Neutral settings are 1.0. Their hash joins the calibration report.
- **Interactions** (FM-style rock-paper-scissors) are a second table. Each entry is: when my
  setting X meets the opponent's setting Y, these levers change. Examples:
  - a high defensive line against a counter-attacking side raises `allow_quality`;
  - a high press against a side that goes long gains less (`allow_rate` back to about 1.0);
  - a low block against a team that shoots from distance gives up more long shots.
- **Why levers**: before the positional engine, the quick sim cannot place players. Levers make
  every option act through the calibrated mechanisms (shots, xG, fouls, possession). The sizes
  stay data, so calibration and the exploit check can tune them.

## R3. Effect sizes

- Published analytics give **directions** reliably:
  - pressing trades turnovers for space behind (StatsBomb and PPDA studies; Klopp's Liverpool:
    high xG for and against);
  - counter-attacking sides take fewer but better shots (higher xG per shot);
  - a leading team gives up possession and shots, and a trailing team pushes (Lago et al.
    2007/2009; StatsBomb "Score effects").

  Sizes are rarely published in comparable form.
- **Decision**: sizes are bounded estimates.
  - A single option moves a lever by at most ±15%.
  - A mentality step moves it by about 5–8%.
  - Every option has at least one cost lever moving the other way.
  - The bounds are refined by two checks:
    - the **calibration gate**, run with AI styles on (the realistic world);
    - the **exploit check**: the maximum gain over neutral is ≤ 0.20 points per match, and no
      tactic is best against every style.
  - The positional engine (007) will replace many levers with real positioning.
- **The table values are pre-pressure.** The `possession` lever also adds attacking pressure
  (`context.possession_pressure`, 2% per point of possession shift; see R6). So an option's real
  effect on shots is its `shot_rate` value *plus* that pressure. Read the `shot_rate` sizes in
  `effects.toml` with this in mind.
- **Owner decision (review of 006)**: role levers count per player, with the same 1/11 share as
  player instructions. A role's main effect is player fit (role suitability scales the player's
  contribution); its team levers are small. A test keeps role-only stacking (the best role for a
  lever in every slot) inside one option's ±15% budget. The exploit check (T012) may retune the
  role values.

## R4. Roles

- **Decision**: in `reference/tactics/roles.toml`, each role has:
  - its phase (IP or OOP) and the positions it is valid for;
  - **key attributes** (role suitability = weighted mean of those attributes, 1–20);
  - the **locked player instructions**;
  - small lever modifiers (e.g. a Poacher raises the forward's `chance_quality` share, a
    Pressing CM adds `foul_rate` and lowers `allow_rate`).
- **Effect on ratings**: the player's contribution to attack and control (IP role) or defence
  (OOP role) is scaled by `0.85 + 0.15 · role_suitability / position_suitability` (capped
  0.8–1.1). Playing the right player in the right role matters, without overpowering the
  position familiarity that 001 and 003 already use.

## R5. AI styles and adaptation

- **Styles** live in `reference/tactics/styles.toml` as full tactics: Posse de bola
  (possession), Contra-ataque (counter), Pressão alta (high press), Jogo direto (direct), Bloco
  baixo (low block) and Equilibrado (balanced). Each style lists its key squad traits.
- **Assignment** is deterministic from squad features:
  - the control composite against attack;
  - the pace of the attackers;
  - defensive strength;
  - reputation.

  A seeded manager profile (a preference weight per style) breaks near-ties, so styles vary
  plausibly.
- **Before the match**: the strength ratio and the venue shift the mentality and the line of
  engagement (a big underdog away goes at most Cautious and mid block).
- **During the match**: an AI side trailing after minute 70 steps its mentality up; one
  leading by 2 or more steps it down. This is on top of 003's game state.

## R6. Calibration and the exploit check

- **Calibration**: the harness gives every club its AI style, with adaptation. The PR and
  milestone gates must pass, so the quick sim is refitted with styles on.
- **Refit with styles on (T011), model 1.2.** It ran as coarse rounds, then a polish on the PR
  sample, with the tuner bounds on `state.level` (to 0.5) and `state.settled` (to 0.35) widened.
  - **Main moves:**
    - `trend_start` 0.94 → 0.80;
    - `settled` 0.15 → 0.108;
    - `yellow_per_foul` 0.241 → 0.226;
    - `direct_red_per_foul` 0.00053 → 0.00096.
  - **Refit consequence for spec 003's caution behaviour.** `caution.foul` goes 0.347 → 0.138 and
    `caution.card` 0.2 → 0.082. A booked player now holds back more strongly than in model 1.1:
    the share of booked players who get a second yellow is 0.057 with the caution on, against
    0.120 with it off.
  - **First result (blocked).** Against the old targets, the PR gate failed on 3-goal games
    (21.1%, band floor 21.3%), and the milestone gate on 3-goal games (20.2%) and 0-0 games
    (9.4%). Styles, tactic levers, role factors and the AI's late steps were each ruled out by
    switching them off.
- **Target recount (data correction).** The league targets counted 720 matches, taken before
  the 2025 season ended. They were recounted from the Wikipedia results matrices of Série A
  2024 and 2025 (raw wikitext, `|match_XXX_YYY = a–b`; 380 matches per season, 760 in all). A
  peer session recounted independently and got identical numbers.
  - **Totals:** 0 goals 7.0%, 1 goal 20.5%, 2 goals 25.8%, 3 goals 24.5% (2024: 27.4%,
    2025: 21.6%), 4 goals 13.0%, 5 or more 9.2%.
  - **Mean** 2.484 goals per match.
  - **Variance/mean 0.887.** Real totals are under-dispersed, while the quick sim is near
    Poisson.
  - **Bands:** each one is re-centred on the recount, with the same width.
- **Score-dependent openness (owner decision).** Two mechanisms were added, to pull totals
  towards the middle without only adding late goals:
  - `state.goalless`: in a 0-0 game both sides push harder, growing to the full value by
    minute 90.
  - `state.respond` and `respond_minutes`: for 10 minutes after conceding, a side pushes harder.

  Paired-seed tests check the directions: the goalless push means fewer 0-0s, and the response
  means fewer 1-goal games.
  - **What the experiments showed.** The goalless push cuts 0-0s strongly, but it moves them to
    2-goal games, not 3. The response adds spread (more 5+ games), so the tuner shrinks it to
    0.038.
  - **Refit settings.** The goals-per-match target is weighted 3× in the loss, so the mean
    cannot drift low again.
- **Refit result (model 1.2).**
  - **PR gate: passes.** 3-goal games 21.4%, 0-0 7.8%, 2.47 goals per match. Exploit check:
    best gain +0.157 (very attacking), no dominant tactic.
  - **Milestone gate: one primary miss.** 3-goal games are at **20.48%** against a floor of
    20.5%, about 3 matches short in 13,200. Everything else passes.
  - **Warning (secondary).** Goals after minute 75 are 31.6% (PR) and 32.2% (milestone),
    against a band up to 31%.
  - **Caution behaviour (spec 003).** `caution.foul` goes 0.347 → 0.069 and `caution.card`
    0.2 → 0.070, so a booked player holds back much more than in model 1.1: second yellows per
    booked player are 0.057 with the caution on, against 0.125 with it off.
- **Exploit check**: a new section of the PR gate.
  - **Setup**: a grid of the 6 style tactics plus single-option variations from neutral,
    played against each of the 6 AI styles. Mirrored strength: the same club meets itself,
    so tactics are the only difference.
  - **Size**: 120 matches per pair at home and 120 away.
  - **Report**: the points-per-match matrix, each tactic's advantage over neutral, and
    whether any tactic is best against every style.
  - **Gate**: a dominant tactic, or a gain over 0.20 points per match, fails it.
- **As built**:
  - **Grid.** The grid has about 70 tactics:
    - neutral;
    - the 6 styles;
    - the 6 other mentalities;
    - the two extreme settings of every team instruction. `progress_through` is left out, since
      it depends on the opponent's flanks.
  - **Stack.** A last row, the *stack*, combines every option that gained on its own. It is the
    tactic a player hunting for an exploit would build.
  - **Seeds and sides.** The mirrored club is a mid-table one (União Operária), so tactics are
    the only difference. Seeds are common: every tactic meets the same random numbers, so each
    gain over neutral is a paired comparison.
  - **Size and design (owner decisions, second review).** It is a two-stage screen with a
    holdout, so the noise that picks a winner does not also inflate its measured gain:
    1. The whole grid plays 20 matches per venue per pair on one seed set. This stage ranks the
       single options and builds the stack.
    2. A fresh seed set plays 60 matches per venue per pair (120 per pair) for the fixed entries
       (neutral, styles, mentalities), the 10 best single options from stage 1, and the stack.
       The report and the gate use these holdout numbers only.

    The milestone sizes are doubled. The PR gate runs the check in about 2–3 minutes. A process
    pool was tried, but it is blocked in the build sandbox, so the check stays serial.
  - **Styles in the grid run without their style**, as the user would run them, so they get no
    AI adaptation during the match. The opponent keeps its style and adapts.
- **Finding (first run).** Possession bought by a tactic only moved the reported share, so every
  option that trades shots for the ball lost points. Direct play gained everywhere, and the
  stack reached +0.23.
  - **Fix.** Each percentage point of possession shift from the tactic now adds 2% to that side's
    attacking pressure (`effects.toml` `context.possession_pressure`).
  - **Second run.** The best tactic gains +0.07, the stack +0.03, and no tactic dominates.
    Defensive mentalities lose about 0.14 points per match at equal strength, which is
    realistic.

## R7. Persistence and reports

- **Save format v3** adds the `tactic` table (the user's tactic as JSON), migrated from v2.
- **Match reports** gain `home_tactic` and `away_tactic` summaries:
  - the IP and OOP formations;
  - the mentality;
  - the style id;
  - a hash of the full tactic.

  The full user tactic is in the save; AI tactics can be rebuilt from style and seed.
