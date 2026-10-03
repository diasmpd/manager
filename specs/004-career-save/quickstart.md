# Quickstart: Career Save and Game Loop (004)

Run from the repository root on Windows (PowerShell), with the `.venv` from 001 activated.

## 1. Checks

```powershell
cd core; ruff check .; mypy; pytest -q -m "not milestone"; cd ..
```

## 2. Start a career (US1)

```powershell
python -m manager_core career new teste --club alvorada
python -m manager_core career list
python -m manager_core career status teste
```

Expected:
- a save `saves/teste.sqlite`;
- the draw and Alvorada's first match;
- the status shows the date before the first match.

## 3. Play (US2, US3)

```powershell
python -m manager_core career continue teste      # stops before Alvorada's first match
python -m manager_core career continue teste      # plays it, stops at the next stop
python -m manager_core season --career teste table
python -m manager_core career status teste        # suspensions, if any
```

Expected:
- each continue stops at Alvorada's match days, competition events or the season end;
- `saves/autosave.sqlite` appears after a week of play;
- suspended players are listed and do not appear in the next match report.

## 4. Seasons (US4)

```powershell
python -m manager_core career continue teste --to-season-end
python -m manager_core career continue teste      # rollover to the next season
python -m manager_core career history teste
python -m manager_core season --career teste groups
```

Expected:
- the history shows the champion and the relegated and promoted clubs;
- the new season has the two promoted clubs instead of the relegated ones;
- squads are full again.

## 5. Save and load (US1)

```powershell
python -m manager_core career save teste --as teste-copia
python -m manager_core career continue teste-copia
python -m manager_core career continue teste
```

Expected: both copies stop at the same place with the same results.
