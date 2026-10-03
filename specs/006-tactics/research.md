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
- **Exploit check**: a new section of the PR gate.
  - **Setup**: a grid of the 6 style tactics plus single-option variations from neutral,
    played against each of the 6 AI styles. Mirrored strength: the same club meets itself,
    so tactics are the only difference.
  - **Size**: 120 matches per pair at home and 120 away.
  - **Report**: the points-per-match matrix, each tactic's advantage over neutral, and
    whether any tactic is best against every style.
  - **Gate**: a dominant tactic, or a gain over 0.20 points per match, fails it.

## R7. Persistence and reports

- **Save format v3** adds the `tactic` table (the user's tactic as JSON), migrated from v2.
- **Match reports** gain `home_tactic` and `away_tactic` summaries:
  - the IP and OOP formations;
  - the mentality;
  - the style id;
  - a hash of the full tactic.

  The full user tactic is in the save; AI tactics can be rebuilt from style and seed.
