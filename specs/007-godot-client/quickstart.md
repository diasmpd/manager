# Quickstart: Godot Desktop Client (spec 007)

How to install, launch and check the desktop client. Run from the repo root in PowerShell.

## 1. One-time setup

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "core[dev]"
.\tools\setup_client.ps1
```

`setup_client.ps1`:
- downloads Godot 4.7.2 (win64) into `tools\godot\` and checks its SHA-512;
- creates a **Manager** shortcut on the desktop.

Running it again is safe.

## 2. Play

- Double-click **Manager** on the desktop. No console window appears.
- The careers screen lists your saves. Open one, or start a new one: pick a name and a club.
- Controls:
  - **Continuar** (or Space) advances the game;
  - **X** opens the tactics;
  - **Esc** goes back.
- Closing the window saves the career.

Expected: the same game as the terminal UI (`python -m manager_tui NAME`), in a window.

## 3. Checks

```powershell
cd core; ruff check .; mypy; pytest -q -m "not milestone"; cd ..
.\tools\godot\godot.exe --headless --path client -s res://tests/run_tests.gd
```

Expected: everything passes. The core tests cover:
- every contract method;
- the framing;
- the version handshake;
- the client–facade parity season.

The client tests cover:
- each screen loading a canned answer;
- the request queue;
- the error display;
- the version refusal;
- a smoke run against the real core.

## 4. Parity checklist (SC-005)

Each terminal UI feature and its counterpart in the window. ✅ means it is covered by the
automated headless session (`client/tests/test_screens.gd`); ☑ means it is implemented and
checked through the core contract tests, but not driven through the window by a test.

- ✅ Home: date, club, next match, position, latest news
- ✅ Continuar to the next stop; ☑ season end, then the next season
- ✅ Team selection: XI on the formation, bench and squad, confirm; ☑ swap, formation,
  assistant, refusal of a suspended player, no-goalkeeper warning
- ✅ Tactics: mentality change and confirm; ☑ OOP formation, instructions by phase, IP and
  OOP roles with suitability, player instructions with locks, set-piece takers and setups,
  reset, notice of lost choices after a formation change
- ✅ Match day: the feed, then the stats; ☑ the speeds and skip
- ✅ Squad, and a player profile
- ✅ Tables (overall) ☑ (groups) and fixtures
- ✅ Calendar by month
- ✅ News
- ☑ Save on quit; reopen and resume (the core saves on `shutdown`, tested in the contract)
- ✅ New career; ☑ the saves list

## 5. Failure checks

- Rename `.venv` temporarily, then launch: the window explains that the core could not start.
- End the `pythonw.exe` process from Task Manager during play: the window says so and offers to
  restart.
