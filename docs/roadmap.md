# Roadmap

Each line is one Spec Kit feature (`specs/NNN-name/`), built on its own branch and merged by PR.
The order follows dependencies. Spec numbers are assigned when `/speckit-specify` runs, so the
numbers here are indicative.

## Milestone 0 — Prototype: Campeonato Mineiro

Goal: play a full Campeonato Mineiro season as one club, using a fictional or sample dataset and,
once collected, real MG club data.

| # | Feature | Status |
|---|---|---|
| 001 | Core domain model: clubs, players with FM attributes (incl. hidden), positions, data import format and a fictional sample dataset | ⏳ next |
| 002 | Tactics model: formations, roles and duties, team and individual instructions, set pieces | — |
| 003 | Positional match engine: continuous movement, calibration harness, smart player behaviours (card caution, energy management, game state) | — |
| 004 | Match report: stats, xG, FM-style player ratings, PT-BR commentary | — |
| 005 | Quick sim (statistical), validated against 003 | — |
| 006 | Competitions and calendar: Campeonato Mineiro format, day-by-day calendar | — |
| 007 | Career save (SQLite) and the day-by-day game loop | — |
| 008 | Local API contract between the core and the client | — |
| 009 | Godot client shell: home, squad, tactics, table, text match view | — |
| 010 | Assistant: suggestions and optional auto-subs | — |
| 011 | Real-data import for MG clubs (into `manager-data`) | — |

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
| Had to sub every booked player to avoid a red card | Booked players ease off tackles automatically, with a trade-off (lose more duels) | 003 |
