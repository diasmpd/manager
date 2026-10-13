# Quickstart: 2D Match View

## Watch a match

1. Start the desktop client, open a career and **Continuar** to a match day; confirm the team.
2. The match opens on the pitch. The controls, left to right:
   - **1× 2× 4× 8×**: the speed, in times real time;
   - **Até o fim**: plays to full time without drawing;
   - **Pausar** (or Space): the pitch stops within a second, at the moment the core is at;
   - **Texto / Campo**: the feed, or the pitch (the choice is remembered);
   - **Melhores momentos / Jogo completo**: only the goals, shots on target, penalties and red
     cards with the seconds around them, the clock running on in between (remembered too);
   - **Substituições** and **Tática**: as before, from the moment on screen.
3. Click a disc to see who it is.
4. At full time **Rever** plays the match again; **Voltar** comes back; **Continuar** goes on.
5. Later: **Calendário**, select a played match marked ▶, **Rever** (or double-click).

In the replay: drag the timeline, or use a button under it to go to a goal or a card.

## Check it

```powershell
cd core; pytest -q tests/integration/test_match_view.py tests/unit/test_positional_engine.py
cd ..; .\tools\godot\godot_console.exe --headless --path client -s res://tests/run_tests.gd
.\tools\godot\godot_console.exe --headless --path client -s res://tests/run_tests.gd -- test_playback
```

Screenshots of every screen, the pitch and the replay included (needs a window):

```powershell
$env:MANAGER_SAVES = "$env:TEMP\manager-shots"
.\tools\godot\godot_console.exe --path client -s res://tests/screenshots.gd -- $env:TEMP\manager-shots
```

## In a git worktree

A worktree has no `.venv` and no `tools\godot`. Point the client at the main checkout's Python and
at this worktree's source:

```powershell
$env:MANAGER_PYTHON = "C:\path\to\Manager\.venv\Scripts\pythonw.exe"
$env:PYTHONPATH = "$PWD\core\src"
C:\path\to\Manager\tools\godot\godot.exe --path client
```

## What the pitch draws

Everything on the pitch comes from the positional record (two samples a second) through the
local API 1.4: `match.start` gives the line-ups and kits, `match.advance` with `frames_from` the
positions, `match.record` a whole played match, `match.passages` the highlights ahead. The values
behind the kits and the highlights are in `core/src/manager_core/reference/match_view.toml`.
