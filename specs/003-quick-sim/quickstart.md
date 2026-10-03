# Quickstart: Quick Sim (003)

Validation guide for the owner. Run from the repository root on Windows (PowerShell), with the
`.venv` from 001 activated.

## 1. Checks

```powershell
cd core; ruff check .; mypy; pytest -q; cd ..
```

The suite covers:
- per-match invariants on thousands of simulated matches (SC-005);
- determinism, including a match replayed alone (SC-003);
- game-state behaviour (late goals, chasing, red cards, caution with its trade-off);
- shootouts by player ability;
- 002's season invariants with the quick sim (1,000 seasons under `slow`).

## 2. A season with real-looking results (US1)

```powershell
python -m manager_core season table
python -m manager_core season fixtures --club alvorada
```

Expected:
- scores look like Brazilian football (mostly 1–0, 1–1, 2–1, with a few big wins);
- there is no "(provisório)" mark;
- the strongest clubs (Vale do Ouro, Serra Negra, Alvorada) are usually near the top, but not
  always.

## 3. A match report (US2)

```powershell
python -m manager_core season fixtures --round 1          # pick a match id
python -m manager_core season match primeira-fase-r01-01
python -m manager_core season scorers
```

Expected:
- a stat line for both sides;
- goals with minutes, scorers and assisters;
- the cards and the substitutions;
- a top-scorer list led by forwards.

## 4. Calibration (US5)

```powershell
python -m manager_core calibrate
python -m manager_core calibrate --baseline core/calibration/quicksim-baseline.json
```

Expected:
- every primary target shows OK;
- secondary targets show OK or AVISO;
- the caution check shows fewer second yellows with the behaviour on, at a small defensive cost;
- the report ends with the core version, Python version and model hash;
- the run takes under 30 seconds.

Milestone gate (slower, used before closing Milestone 0):

```powershell
python -m manager_core calibrate --gate milestone
```

## 5. Shootouts (US4)

```powershell
python -m manager_core season bracket
```

If a tie went to penalties, `season match <id of the last leg>` lists each kick with the taker.
