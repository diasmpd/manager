# Implementation Plan: Godot Desktop Client

**Branch**: `007-godot-client` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

## Summary

The Milestone 0 game moves into a Godot 4.7 desktop window, with the same screens as the
terminal UI and the Tactics screen.
- **Core side**: a new `manager_core.server` speaks the **local API contract**: one JSON
  message per line over the stdio of a child process. Each method maps to a facade function.
- **Client side**: a Godot project in `client/`. A `Core` autoload manages the process and the
  requests, and one scene per screen draws the answers.
- **Launching**: a setup script fetches portable Godot and creates a desktop shortcut, so the
  game starts with one double-click and no console.

Details: [research.md](research.md). Contract: [contracts/local-api.md](../../contracts/local-api.md).

## Technical Context

- **Languages**:
  - core: Python ≥ 3.12, standard library only (the server uses `json`, `sys` and the facade);
  - client: GDScript on Godot 4.7.2-stable (win64, standard build).
- **Dependencies**: no new Python dependency. Godot is fetched by `tools/setup_client.ps1` into
  the gitignored `tools/godot/`.
- **Storage**: unchanged. The core writes the SQLite saves; the client writes nothing.
- **Testing**:
  - pytest for every contract method, the framing, the handshake and the client–facade parity
    season;
  - a headless Godot runner for the screen scenes, the request queue and the error paths, plus
    a smoke run against the real core.
- **Target**: Windows 11 desktop (owner decision), from 1280×720 up.
- **Performance**: a screen in under 0.5 s; a Continue no slower than the terminal UI plus
  0.2 s; whole-season continues with progress. The JSON for a screen is at most tens of KB.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | No simulation change. |
| II. Determinism | ✅ | One request at a time, in order. A parity test checks a season through the server against the facade. |
| III. Thin client | ✅ | This spec *is* the versioned contract III requires. The client only sends choices and draws results, and every method maps to the facade. |
| IV. Test-first | ✅ | Contract tests come before the server methods, and scene tests before the scenes. |
| V. Manager in control | ✅ | The same assistant proposals as the terminal; the owner confirms. |
| VI. Data rights | ✅ | No data changes. The client ships no player data. |
| VII. Incremental | ✅ | Text match view only, no exported executable, default theme. 2D/3D and export come later. |

## Project Structure

```text
core/src/manager_core/
├── server/
│   ├── __main__.py   # python -m manager_core.server --saves DIR
│   ├── protocol.py   # line framing, JSON-RPC subset, error mapping, progress notifications
│   ├── encode.py     # dataclass/enum/date -> JSON
│   └── methods.py    # one handler per contract method, each calling the facade
├── api.py            # + view.home / match stat rows helpers (research R8), ui strings export
client/
├── project.godot
├── core.cfg          # python path and saves folder (defaults relative to the repo)
├── autoload/core.gd  # process, request queue, signals, version check
├── scenes/           # main, careers, new_career, home, selection, tactics, match_day,
│                     # squad, player, tables, calendar, news
└── tests/run_tests.gd
tools/setup_client.ps1  # fetch Godot 4.7.2 (SHA-512 checked) + desktop shortcut
.github/workflows/ci.yml  # + headless client tests on Windows
```

## Phases

1. **Contract and server** (core):
   - framing and dispatch;
   - encoding;
   - all methods with tests;
   - parity.
2. **Client foundation**:
   - setup script;
   - Godot project;
   - the `Core` autoload (handshake, queue, errors, process lifecycle);
   - the main layout;
   - checking that no console window appears.
3. **Screens**, in the user stories' order:
   - careers and new career;
   - home and Continue;
   - team selection;
   - match day;
   - tactics;
   - squad and player;
   - tables, calendar and news.
4. **Polish**:
   - the parity checklist;
   - headless client tests in CI;
   - docs (README, roadmap with the renumbering, quickstart).

## Complexity Tracking

| Item | Why it is needed | Simpler alternative rejected |
|---|---|---|
| A child process with a stdio protocol | Constitution III requires a contract; the core is Python and the client is Godot | Embedding Python (native build), or HTTP (firewall prompts and ports) |
| A Godot download script | Godot isn't installed and must not need admin rights | Asking the owner to install it by hand (FR-006: one double-click) |
