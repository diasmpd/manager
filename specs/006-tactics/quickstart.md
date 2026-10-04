# Quickstart: Tactics (spec 006)

How to check that tactics work end to end. Run from the repo root in PowerShell, with the
`.venv` from the README.

## 1. Checks

```powershell
cd core; ruff check .; mypy; pytest -q; cd ..
cd tui; ruff check .; mypy src tests; pytest -q; cd ..
```

Expected: everything passes. The tactics tests are:
- `core/tests/unit/test_tactics_*.py`: model, effects, AI;
- `core/tests/integration/test_tactics_engine.py`: statistical directions on paired seeds;
- `core/tests/unit/test_career_tactic.py`: career, facade and save v3;
- `core/tests/unit/test_calibration_exploit.py`: exploit check logic;
- `tui/tests/test_tactics_screen.py`: pilot tests.

## 2. Calibration and the exploit check

```powershell
python -m manager_core calibrate                  # PR gate, with AI styles and the exploit check
python -m manager_core calibrate --gate milestone # the out-of-sample gate
```

Expected:
- every primary metric is OK;
- the line "Exploit tático" names the best tactic, with a gain of at most +0.20 points per match
  over the neutral tactic, and no dominant tactic.

Only the PR gate runs the exploit check, which adds about 2–3 minutes. It is a two-stage screen:
1. about 70 tactics against 6 styles, 40 matches per pair, to rank the options and build the
   stack;
2. a fresh holdout set, 120 matches per pair, for the finalists. The gate uses these numbers.

## 3. Play with a tactic (terminal)

```powershell
python -m manager_core career new tatica --club alvorada
python -m manager_tui tatica
```

- **X** opens the Tactics screen, from the main screen or from team selection.
- **Left list**:
  - the formations (the IP formation comes from the selection; Enter cycles the suggested OOP
    shapes);
  - the mentality (7 levels);
  - every team instruction, grouped by phase;
  - the set-piece setups.

  Enter cycles the highlighted setting.
- **Right lists** (Tab moves between them):
  - roles per slot, each with the player's suitability in brackets. Enter cycles the IP role,
    **O** the OOP role;
  - the highlighted slot's player instructions. 🔒 marks instructions locked by a role, which
    cannot be changed;
  - the set-piece takers. Enter cycles through the XI; "automático" lets the match pick.
- **R** resets to the default tactic; **C** confirms; **Esc** leaves without changes.

Expected:
- the confirmed tactic is saved with the career;
- the next matches use it, and the match report records both sides' tactics (formations,
  mentality, AI style, digest);
- if you change the formation in team selection, the instructions are kept and the roles reset
  to that formation's defaults.

## 4. What the AI does

- Every AI club has a style:
  - Posse de bola (possession);
  - Contra-ataque (counter);
  - Pressão alta (high press);
  - Jogo direto (direct);
  - Bloco baixo (low block);
  - Equilibrado (balanced).

  The style comes from the squad's traits plus a fixed manager preference.
- **Before a match**:
  - a big underdog away plays at most Cautious and no higher than a mid block;
  - a big favourite at home goes one step more attacking.
- **After minute 70**: a side that is trailing steps its mentality up (two steps when two goals
  down); a side leading by two steps it down.
