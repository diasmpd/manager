# Research: Positional Match Engine

The decisions for spec 008. The owner's three decisions (text view plus a record, pause at any
time, and the 3-goal fix inside 008) are in the spec. The choices below are recommendations
recorded for his review, under his standing rule.

## R1. Time, movement and the cost budget

- **Decision**:
  - Fixed time steps of **0.25 s (4 Hz)** over the playing time, stoppage time included.
  - Players and the ball move every step. Players steer towards a target point, limited by
    their speed and acceleration.
  - Off-ball targets are recomputed **every 0.5 s**. On-ball decisions are taken when a player
    receives the ball, and then every 0.5–1 s while he keeps it.
  - The engine is **pure Python**, with no numpy.
- **Measured**:
  - movement of 22 players over 90 minutes: 0.22 s at 4 Hz, 0.44 s at 10 Hz;
  - on-ball decisions: about 4,000 per match, each weighing about 10 options against 11
    defenders, estimated at 0.5–1 s;
  - target: **1–2 s per match**, well inside the constitution's 10 s.
- **Why**:
  - 4 Hz is enough for realistic runs (a sprinter covers 2 m per step) and for a smooth 2D
    replay, since the record is interpolated.
  - FM also decides at key moments and moves players continuously between them.
  - A pure-Python engine keeps the core free of new dependencies (constitution: each dependency
    must be justified).
- **Alternatives**:
  - **10 Hz with numpy**: twice the cost, plus a dependency, for precision M0 doesn't need.
  - **Zone-to-zone "key moments" without continuous positions**: cheaper, but it can't produce
    the positional record (Constitution III) or the positional meaning of tactics.

## R2. What players do (the decision model)

- **Off the ball**: each player's target is his formation slot, chosen by phase.
  - **In possession**: the IP formation slot.
  - **Out of possession**: the OOP formation slot.

  The slot is shifted by these, all as data:
  - the ball's position (the team block slides towards the ball);
  - the team instructions (defensive line height, line of engagement, width, compactness);
  - the role (e.g. a wing-back pushes high in possession, a defensive midfielder holds);
  - player instructions (stay wider, more forward runs).

  The nearest one or two defenders press the ball carrier, as the pressing instructions say.
  Markers follow their nearest opponent in their zone.
- **On the ball**: the carrier scores his options by expected value and picks among them with
  some noise. The noise is lower for better decision-making players.

  | Option | How it is scored |
  |---|---|
  | Pass to each teammate | success chance (distance, passing, vision, pressure, interception by opponents near the line) × the threat of the target spot |
  | Dribble | beating the nearest defender (dribbling, agility and pace against tackling, positioning and pace) |
  | Shoot | the xG of the spot (R3), with composure and long shots |
  | Cross | from wide areas, aimed at a target per the crossing instructions |
  | Clear | in the defensive third under pressure |
  | Hold up | strikers with hold-up play |

  - **Team instructions bias the weights**: passing directness, tempo, shots from distance,
    crossing, patience, dribbling.
  - **Mentality** biases risk.
- **Challenges**: when a presser reaches the carrier, a duel resolves as one of four outcomes:
  - the tackle wins the ball;
  - the carrier keeps it;
  - a foul (from aggression and the tackling instruction; card caution lowers it, as in spec
    003);
  - a card (the card and red-card models from spec 003, applied to a foul that actually
    happened).
- **Keepers**: shot stopping from reflexes, one-on-ones and handling, against the shot's xG and
  placement. The keeper also claims crosses and distributes the ball per the goal-kick
  instructions.
- **Set pieces**: corners, free kicks and penalties start from their spots. Corners use the
  setups and takers from spec 006.
- **Why**: this is FM's structure (attributes × decisions × positions). Every attribute group and
  every 006 option acts through something visible on the pitch (FR-002, FR-007).

## R3. Shots and xG

- **Decision**:
  - A shot's xG comes from a logistic model of distance and angle to goal, plus header or foot,
    a defender in the way, and keeper position. The coefficients are in the published range of
    public xG models: about 0.75 from the penalty spot when unopposed, about 0.10 at 16 m
    straight on, and about 0.03 from 25 m.
  - Finishing turns xG into the shot's quality; the keeper's save chance uses it.
  - Penalties use the spec 003 model, with the taker against the keeper.
- **Why**: a chance's value then follows from where it happens on the pitch, and the engine's xG
  is comparable with the quick sim's and with real data (calibration target "xG ≈ goals").

## R4. Energy and fatigue

- **Decision**:
  - Each player has an energy level that drains with distance and sprinting, scaled by stamina
    and natural fitness, and recovers slowly at walking pace.
  - Low energy lowers top speed and acceleration, and adds noise to decisions.
  - The assistant's automatic substitutions (spec 003) weigh energy, cards and the score.
  - Realistic totals: 9–12 km for outfield players, and a lower sprint share after minute 70.
- **Why**: FR-007, and the roadmap's "energy management". The quick sim's late-game fatigue
  lever (spec 006) becomes physical here.

## R5. Game state and the 3-goal mechanism

- **Decision**: game-state behaviour is a set of **team intents**, applied through the
  positional targets and the decision weights:
  - **trailing late**: a higher line, more players forward, riskier passes (spec 003's chase and
    exposure);
  - **leading by one late**: a deeper block and safer options (protect);
  - **level late**: both sides open up a little;
  - **leading by two or more**: the leading side **relaxes**. It slows its own attacks, its
    concentration drops, and its defending is less tight. The trailing side still pushes for a
    consolation goal.
- **Hypothesis for the 3-goal shortfall (to be validated in the engine first)**:
  - The quick sim's `settled` term slows *both* sides when a lead reaches two. That freezes 2-0s
    and lets 5-0s through.
  - Real matches more often end 2-1 (a late consolation goal) or 3-1, and they rarely run away
    further.
  - The positional engine models the leading side relaxing and the trailing side still pushing.
    If that moves the totals from 2 towards 3 and trims 5+, the quick sim gets the statistical
    counterpart: `settled` is split into a leader that relaxes (it allows better chances and
    attacks less) and a trailing side that keeps its push.
  - The quick sim is then refitted, and both gates must pass with unchanged targets (FR-010).
  - If the hypothesis fails in the engine, the engine's measurements guide the next candidate.
    Two such candidates were tried in 006 and removed (`respond`, `managed`, research R6 of
    006).
- **Why**: the owner chose to fix the shortfall where the realistic mechanism can be seen. The
  006 lesson applies: ground the mechanism in what teams do, then calibrate.

## R6. Calibration and cross-validation

- **Decision**:
  - The positional engine has its own parameter file, `reference/positional/model.toml`, and its
    own tuner, and uses the same targets file and harness.
  - It runs its own sample sizes (Constitution: about 200 per PR, 1,000 or more at the
    milestone):
    - **PR gate: 300 matches** (about 8 minutes at 1.5 s);
    - **milestone gate: 1,500 matches**.
  - Thin samples get noisy primary bands. The PR gate therefore checks the robust metrics:
    - goals per match;
    - the home, draw and away split;
    - shots and on-target shots;
    - cards;
    - xG − goals.

    The milestone gate checks every target.
  - **Cross-validation** (FR-009) plays the same fixtures through both engines and compares the
    distributions (SC-003). It is part of the milestone gate.
- **Why**: one realism yardstick for both tiers (Constitution, two-tier calibration), within a
  CI budget that stays usable.

## R7. Live matches and pause (the owner's decision 2)

- **Decision**: the engine is a stepper object, `LiveMatch`, and the client drives the clock.
  - The server opens the user's match with `match.start`. The client calls
    `match.advance {seconds}` at its chosen speed, and each call returns the new feed lines and
    the state (minute, score, stats).
  - **Pausing means the client stops calling `match.advance`.** No pause message is needed.
  - While paused, the client can use `match.substitute`, `match.tactic` and `match.state`.
    Decisions are stamped with the match time and recorded.
  - `match.finish` plays to full time when the owner skips ahead. The result is committed to the
    season, and the rest of the match day goes on as before.
  - Non-interactive play (the CLI, tests, `continue` without a client) plays the match straight
    through, with no decisions.
- **Closing the window mid-match** (spec edge case): the match is **not** saved half-played. The
  career resumes before the match day. The match is deterministic from its seed, so replaying
  without decisions gives the same match. With different decisions the owner can manage it
  differently.
- **Why**:
  - Pause at any time, with exact replay from the seed plus decisions (FR-005, FR-006).
  - No threads in the core: the server stays one-request-at-a-time (spec 007, R3).

## R8. The positional record

- **Decision**:
  - Samples at **2 Hz**: the ball (x, y, height) and the 22 players (x, y), in centimetres, as
    int16.
  - Event markers point to sample indices.
  - Stored zlib-compressed in a new `records` table: one blob per user match, about 200–400 KB.
    Background matches have none.
  - Save format v4, with a v3 → v4 migration (an empty table).
  - The facade can read a record back. Its contract method arrives with 008b (the 2D view).
- **Why**: FR-004 and Constitution III. 2 Hz interpolates smoothly in a 2D view. A season of
  about 22 user matches adds about 5–9 MB per save.

## R9. Career integration

- **Decision**:
  - The quick-sim provider gains a **precomputed result** slot. A user match played live puts
    its Result and report there before the match day is continued, and the provider returns
    it. This is the same pattern as `RecordedProvider` for loaded saves.
  - When nothing is precomputed (CLI and tests), the provider plays user matches through the
    positional engine itself.
  - Old saves keep their recorded results, and nothing is re-simulated.
- **Why**: the season, discipline, news and table code stays untouched (FR-003).
