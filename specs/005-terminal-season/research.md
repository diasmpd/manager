# Research: Playable Season in the Terminal (005)

Each entry: Decision / Rationale / Alternatives considered.

## R1. TUI framework: Textual

- **Decision**: Textual (MIT, 8.x), in a separate package `tui/` (`manager_tui`). Its
  `pyproject.toml` depends on `manager-core` and `textual>=8.2,<9`. The core keeps no runtime
  dependencies.
- **Rationale**:
  - Full-screen layouts, keyboard bindings, tables and CSS-like styling.
  - It works in Windows Terminal and the classic console.
  - `App.run_test()` gives a headless pilot for scripted tests and snapshots (Constitution IV
    for UI code).
- **Alternatives**: curses (no native Windows support); prompt_toolkit (lower level, more code
  per screen); `rich` alone (no interaction).

## R2. The user's selection lives in the core

- **Decision**:
  - **Storage.** `Career.selection: Selection | None` holds the formation, starters
    (slot index → player id) and bench.
  - **Playing with it.** `QuickSimProvider` gains per-club *overrides*: for the user's club,
    the confirmed selection is turned into a `TeamSheet` and used as is. Suspensions are
    validated before confirming. Other clubs keep the assistant's sheets.
  - **Persistence.** The selection stays from match to match, as in FM. When it becomes
    invalid (a player is suspended), it is re-proposed with a notice.
- **Rationale**: the UI holds no rules (Constitution III). The same selection would come from
  the 010 Godot client through the same facade.

## R3. Save format v2

- **Decision**: add `selection(json TEXT)`. The v1 → v2 migration creates the empty table.
  This is 004's migration hook used for the first time, with a test that loads a v1 file.

## R4. Match day feed

- **Decision**: on confirming the selection, the core plays the day and the UI receives the
  report. `match_feed(report)` (core, pure) returns `FeedLine`s for:
  - kick-off;
  - each goal, card, substitution and missed penalty;
  - half-time and full time.

  Shots on target are summarised per 15-minute block ("Alvorada pressiona: 3 finalizações").
  The UI shows the lines at a chosen speed. The result never depends on the speed.
- **Rationale**: the quick sim decides the whole match at once, and the feed is presentation
  (FR-008). Spec 007 will replace the feed source with the positional engine's record.

## R5. Stars and squad stats

- **Decision**:
  - **Stars**: from 0.5 to 5 in half steps, by the player's CA percentile within his squad.
    The best player of the squad gets 5. CA is never shown as a number, which is FM's
    "team-relative" view.
  - **Season stats** (appearances, minutes, goals, assists, yellow and red cards) are
    aggregated from the current season's reports by a facade function.

## R6. News

- **Decision**: `career_news(career)` builds dated items from:
  - season events (the draw, qualifications, titles, relegations);
  - the user club's results;
  - suspensions of the user club's players (from the ledger as it changes, recomputed by
    walking the results);
  - season records.

  Items are newest first, with text through i18n keys.

## R7. Testing the UI

- **Decision**:
  - **Pilot tests.** Textual's pilot drives scripted sessions (US1–US3). Each screen gets
    render tests that assert key text at 100×30.
  - **Snapshot images.** `pytest-textual-snapshot` is not added. Text assertions avoid a
    second dependency and fragile SVGs.
  - **Async.** The UI tests need `pytest-asyncio`, a dev-only dependency of the TUI package.
- **CI**: the workflow also installs `tui/` and runs its tests.

## R8. Performance

- **Screens**: they read facade views built from the in-memory career. Screen switches stay
  under 0.1 s.
- **Continuar**: 004's loop already takes under 1 s.
- **Startup**: loading a save (≤ 0.5 s) dominates.
