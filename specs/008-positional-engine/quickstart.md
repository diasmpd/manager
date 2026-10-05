# Quickstart: Positional Match Engine (spec 008)

Run from the repo root in PowerShell, with the `.venv` from the README.

## 1. Checks

```powershell
cd core; ruff check .; mypy; pytest -q -m "not milestone"; cd ..
.\tools\godot\godot_console.exe --headless --path client -s res://tests/run_tests.gd
cd tui; pytest -q; cd ..
```

Expected: all pass. The 008 tests are:
- `core/tests/unit/test_positional_*.py`: geometry, movement, decisions, xG, energy, the record;
- `core/tests/integration/test_positional_behaviour.py`: card caution, fatigue, chasing,
  protecting, and the positional meaning of tactics, on paired seeds;
- `core/tests/integration/test_positional_replay.py`: the same seed and decisions give the same
  match;
- `core/tests/integration/test_live_match.py`: the contract methods;
- the client and TUI pause tests.

## 2. Calibration

```powershell
python -m manager_core calibrate --engine positional              # PR gate (300 matches)
python -m manager_core calibrate --engine positional --gate milestone  # all targets + cross-validation
python -m manager_core calibrate                                  # the quick sim, now with the 3-goal fix
python -m manager_core calibrate --gate milestone
```

Expected:
- every primary metric is OK on both engines;
- the quick sim's milestone gate passes, with 3-goal games at or above 20.5%;
- cross-validation agrees within the SC-003 tolerances.

## 3. Play

Double-click **Manager**, open a career and continue to a match.
- The match plays live. **Pause** (Space or the button) stops it.
- While paused, **Substituições** and **Tática** apply changes from that minute.
- **Continuar** resumes.
- **Pular para o fim** plays to full time.

Expected:
- the feed and the stats come from the positional simulation;
- a substitution shows in the feed at the pause minute;
- closing the window mid-match resumes the career before that match day.
