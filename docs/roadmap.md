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
| 001 | Core domain model: clubs, players with FM attributes (incl. hidden), positions, and the data **import format** (format only: no SoFIFA→FM conversion), plus a fictional sample dataset | ⏳ next |
| 002 | Competitions and calendar: Campeonato Mineiro format, day-by-day calendar | — |
| 003 | Quick sim (statistical), calibrated independently against real-data targets | — |
| 004 | Career save (SQLite) and the day-by-day game loop | — |
| 005 | **Playable Mineiro season from the terminal** (Python TUI): includes basic squad and lineup selection (and formation choice, if 001 models it), so the user makes real decisions before 006 | — |
| 006 | Tactics model: roles and duties, team and individual instructions, set pieces; custom formations with separate attacking/defending shapes and free player placement (owner request) | — |
| 007 | Positional match engine: continuous movement, smart player behaviours (card caution, energy management, game state), cross-validated with 003 | — |
| 008 | Match report: stats, xG, FM-style player ratings, PT-BR commentary | — |
| 009 | Assistant: suggestions and optional auto-subs | — |
| 010 | Local API contract + Godot desktop client (text match view, squad, tactics, table) | — |
| 011 | Real-data import for MG clubs (into `manager-data`), including an attribute-synthesis model | — |

### Notes for specific specs
- **007 (positional engine)**: in pure Python, 22 players plus the ball at 5–10 Hz over 90 minutes
  is about 27–54k ticks with decisions, which is tight for the 10 s budget. The plan must decide
  early between a coarse tick with "key moments" (closer to FM) and numpy for the movement maths.
- **011 (real data)**: most Mineiro clubs other than Atlético, Cruzeiro and América are not in
  SoFIFA, so there are no ratings to convert. Transfermarkt has squads, ages and values but no
  attributes. 011 therefore needs an attribute-synthesis model (position + age + market value +
  league level → FM attributes), with SoFIFA conversion used only where ratings exist.
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

## Later

2D match view → Libertadores and Sul-Americana → 3D match view → online leagues with friends.

## Pain-point log

Annoyances reported by the owner, each linked to the spec that fixes it.

| Pain point | Fix | Spec |
|---|---|---|
| Had to sub every booked player to avoid a red card | Booked players ease off tackles automatically, with a trade-off (lose more duels) | 007 |
