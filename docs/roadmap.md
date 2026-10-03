# Roadmap

Each line is one Spec Kit feature (`specs/NNN-name/`), built on its own branch and merged by PR.
The order follows dependencies. Spec numbers are assigned when `/speckit-specify` runs, so the
numbers here are indicative.

## Milestone 0 — Prototype: Campeonato Mineiro

Goal: play a full Campeonato Mineiro season as one club, using a fictional or sample dataset and,
once collected, real MG club data.

The order puts a playable loop first: a full season can be played from the terminal (CLI/TUI) by
spec 005, using the quick sim. The positional engine and the desktop client follow on top of a
working game.

| # | Feature | Status |
|---|---|---|
| 001 | Core domain model: clubs, players with FM attributes (incl. hidden), positions, and the data **import format** (format only: no SoFIFA→FM conversion), plus a fictional sample dataset. [Spec](../specs/001-core-domain-model/spec.md) | ✅ done (PR) |
| 002 | Competitions and calendar: Campeonato Mineiro format as data (rulesets), draw, fixtures, dates, tables and tiebreakers, knockouts, Troféu Inconfidência, outcomes, day-by-day calendar with reserved windows. [Spec](../specs/002-competitions-calendar/spec.md) | ✅ done (PR) |
| 003 | Quick sim (statistical), calibrated independently against real-data targets: minute-by-minute events from FM attributes (xG, cards per player, substitutions, game state, booked-player caution), player-based shootouts, calibration harness with PR/milestone gates. [Spec](../specs/003-quick-sim/spec.md) | ✅ done (PR) |
| 004 | Career save (SQLite) and the day-by-day game loop: saves with weekly autosave, "Continuar" that stops at events, suspensions (real rules), season rollover with promotion, ageing, development, player-decided retirement and youngsters. [Spec](../specs/004-career-save/spec.md) | ✅ done (PR) |
| 005 | **Playable Mineiro season from the terminal** (Python TUI): includes basic squad and lineup selection (and formation choice, if 001 models it), so the user makes real decisions before 006. [Spec](../specs/005-terminal-season/spec.md) | ✅ done (PR) |
| 006 | Tactics model: roles and duties, team and individual instructions, set pieces; custom formations with separate attacking/defending shapes and free player placement (owner request) | ⏳ next |
| 007 | Positional match engine: continuous movement, smart player behaviours (card caution, energy management, game state), cross-validated with 003 | — |
| 008 | Match report: stats, xG, FM-style player ratings, PT-BR commentary | — |
| 009 | Assistant: suggestions and optional auto-subs | — |
| 010 | Local API contract + Godot desktop client (text match view, squad, tactics, table) | — |
| 011 | Real-data import for MG clubs (into `manager-data`), including an attribute-synthesis model. Also covers (moved from 001): tolerant reading of files re-saved by pt-BR Excel (format v1.1) and the manual-edit audit trail | — |

### Open items
- **Confirm in the official FMF 2026 regulation** (002 used press sources): tiebreaker order,
  semifinal pairing, and the Troféu Inconfidência entrants and dates (5th–8th skipping
  semifinalists vs. the best 4 outside the semifinals). Each one is a value in
  `reference/competitions/mg-modulo-i-2026.toml`, so a fix is a data change.
- **Calendar dates are approximate**: FIFA windows (default and 2027), Copa do Brasil and
  Brasileirão windows in `reference/calendar/`. Refine when those competitions are specified.

### Notes for specific specs
- **003 → 004/005**: the quick sim records cards per player, so suspensions (3 yellows, reds)
  can be built in the career loop. Team sheets are cached per dataset, and 004 must
  invalidate them when squads change (transfers, injuries). Calibration secondary targets
  (shots, fouls) still need a strong source.
- **007 (positional engine)**: cross-validate against the quick sim with the same targets file
  (`reference/calibration/quicksim-targets.toml`) and the same harness samples.
- **004 (career save)**: a season's participants come from the previous season's outcomes
  (relegated clubs leave, promoted clubs from Módulo II enter). 002 picks participants by state
  or an explicit list. 004 also persists `Season` (today the CLI rebuilds it from the seed).
- **007 (positional engine)**: in pure Python, 22 players plus the ball at 5–10 Hz over 90 minutes
  is about 27–54k ticks with decisions, which is tight for the 10 s budget. The plan must decide
  early between a coarse tick with "key moments" (closer to FM) and numpy for the movement maths.
- **011 (real data)**: most Mineiro clubs other than Atlético, Cruzeiro and América are not in
  SoFIFA, so there are no ratings to convert. Transfermarkt has squads, ages and values but no
  attributes. 011 therefore needs an attribute-synthesis model (position + age + market value +
  league level → FM attributes), with SoFIFA conversion used only where ratings exist.
  - Audit trail (moved from 001): a per-record hash shows *that* a record changed, not *which
    field*. Decide whether to store previous canonical values so field-level diffs are auditable.
    `record_flags.csv` flags persist across exports, and only `integrity.csv` is rewritten.
  - Re-calibrate the CA mapping (001 research R8) against named, dated sources.
- **006 (tactics)**: now also carries custom formations, separate in/out-of-possession shapes and
  free player placement, so it will likely split into two specs (tactics model, then formation
  editor/shapes).
- **Lessons from `prototype/`** (for 001 and 006):
  - Pick the XI with a real assignment (Hungarian algorithm or "most constrained slot first"),
    not formation order.
  - FM has 7 mentality levels (Very Defensive … Very Attacking) and finer instruction steps.
    Match that or record why not.
  - Access attributes explicitly (`player.attrs.x`); avoid `__getattr__` delegation.
  - Keep: formation slots in metres, hidden attributes (temperament drives the reaction to a
    booking), and the card-caution trade-off maths.

## Milestone 1 — v1: Estaduais + Brasileirão

- All Estaduais, Série A–D and Copa do Brasil.
- World leagues simulated in the background (South America, Europe top 5, other major leagues).
- Transfers and contracts, training and development, youth academy.
- Finances and board, scouting, staff, media and morale.
- Full real-data import with provenance.

### Living world (owner's five-year picture, see vision)

Features to place in later milestones once the core game is complete. Each will get its own spec:

- **Match importance** model (competition, stage, rivalry, stakes): the input for everything
  below.
- **Supporters**: attendance, travelling fans, home pressure and city mood by importance.
- **Officials**: a referee pool with levels and styles, assigned by competition and
  importance.
- **Match-day events**: build-up, entrance ceremonies and city events for finals and derbies.
- **Media and morale** reacting to the stakes (overlaps with v1's media and morale).

### Deferred from 006

- **OOP shape mapping**: map each IP slot to its OOP-formation position, validate OOP roles
  against that position, and give the OOP shape its own effects. With 006b/007.

## Later

2D match view → Libertadores and Sul-Americana → 3D match view → online leagues with friends.

## Pain-point log

Annoyances reported by the owner, each linked to the spec that fixes it.

| Pain point | Fix | Spec |
|---|---|---|
| Had to sub every booked player to avoid a red card | Booked players ease off tackles automatically, with a trade-off (lose more duels) | 007 |
