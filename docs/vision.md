# Product Vision

A personal football management game for Windows. It aims to be as realistic as Football Manager
while removing the tedious micromanagement found in games like Brasileirinho FC.

This document records the product decisions agreed on 2026-10-02. Each feature spec in `specs/`
refines one part of it.

## Player experience

- **Role**: you manage a real club (Brazil first) through a career, FM-style.
- **Time**: real calendar, advanced day by day ("Continuar"), with transfer windows, the CBF
  calendar and international breaks.
- **Tactics**: full FM depth, with formations, roles and duties per player, team instructions,
  individual instructions and set pieces.
- **Matches**: shown first as text commentary with stats, then a 2D pitch view, then 3D. The
  engine is positional from day one so the later views only replay data it already produces.
- **Smart automation** ("make it yours"):
  - Players act on their own judgment: booked players ease off, tired players manage their energy,
    and behaviour adapts to the score and the minute.
  - The assistant suggests substitutions and tactical changes, and you approve them.
  - Auto-substitutions are optional per category (injury, red-card reshuffle, fatigue).
  - New pain points are added as the owner reports them during development.
- **Career systems** (all FM-benchmarked):
  - Transfers and contracts: negotiations, wages, clauses and loans.
  - Training and development: growth by age and potential, youth academy.
  - Finances and board: budget, revenues and expectations, with the risk of being sacked.
  - Scouting, staff and media: scouts, coaching staff, press conferences, morale.
- **Language**: game in PT-BR. Code and docs in English.

## Realism priorities

1. Match statistics consistent with real leagues: goals, shots, xG, possession, fouls, cards.
2. Tactics that genuinely matter, with no exploit tactics.
3. A believable economy and transfer market between real clubs.
4. Believable player development and ageing, with uncertain potential.

## World

- **Playable focus**: Brazil, with all national divisions (Série A–D), Copa do Brasil and the
  Estaduais.
- **Simulated around it**: South America, Europe's top 5 leagues and other major leagues
  (Portugal, Netherlands, MLS, Saudi Arabia, Mexico, …) for transfers and continental cups.
- **Data**: real clubs and players, gathered from public sources (Transfermarkt for
  values/contracts, SoFIFA-style ratings converted to FM's 1–20 attributes). Stored in the
  private `manager-data` repo, never in this public repo.
  - *Risk*: these sites' terms of use restrict automated scraping. The import spec must define
    a compliant, personal-use collection approach (e.g. manual exports or low-volume fetches).
  - *Coverage gap*: most Mineiro clubs other than Atlético, Cruzeiro and América are not in
    SoFIFA, so there are no ratings to convert. For those clubs, attributes must be synthesised
    from position, age, market value and league level (see roadmap, spec 011).

## Architecture (summary)

| Layer | Choice |
|---|---|
| Simulation core | Python, headless, deterministic (seeded) |
| Match engine | Two tiers: a positional engine for your matches, a statistical quick sim for the rest of the world |
| Saves | One SQLite database per career |
| Client | Godot 4 desktop app (Windows), talking to the core over a versioned local API. Milestone 0 is played through a Python terminal UI first; Godot arrives in spec 010 |
| Online | Not built. The save and API design leave room for "leagues with friends" later |

## Out of scope (for now)

Online multiplayer, mobile, 3D view, women's football and national-team management. These may be
revisited after v1.
