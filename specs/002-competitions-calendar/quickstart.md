# Quickstart: validating feature 002

Run these from the repo root in PowerShell, with the `.venv` from 001 activated.

## 1. Automated checks

```powershell
cd core; ruff check .; mypy; pytest -q; cd ..
```

The suite covers:
- ruleset validation (one broken file per R-code);
- the draw;
- fixture invariants (8 matches, 4 home and 4 away, cross-group only);
- the 66-hour rest rule;
- tiebreak scenarios;
- 200 full seasons, plus 1,000 in the `slow` marker;
- determinism;
- the test ruleset.

## 2. Start a season (US1)

```powershell
python -m manager_core season groups
python -m manager_core season fixtures --round 1
python -m manager_core season fixtures --club vale-do-ouro
```

Expected:
- the 3 strongest clubs (Vale do Ouro, Serra Negra, Alvorada) head groups A, B and C;
- each club has 8 matches against the other groups, 4 at home and 4 away;
- dates run from January to early March.

## 3. Play the season (US2)

```powershell
python -m manager_core season table --group A --date 2027-01-31
python -m manager_core season table --overall
python -m manager_core season bracket
python -m manager_core season outcomes
```

Expected:
- tables mark the semifinal, Inconfidência and relegation zones, with a decided-by note where
  clubs are level on points;
- the bracket shows two-leg semifinals, a single final at the Arena Estadual das Gerais and the
  Inconfidência ties;
- the outcomes show the champion, Inconfidência winner and the 2 relegated clubs;
- all results are marked "(provisório)".

## 4. Determinism

Run `season outcomes` twice and confirm the output is identical. With `--master-seed 1`, the
draw and the champion differ.

## 5. Rules as data (US3)

```powershell
python -m manager_core season rules
$liga = "alvorada,campo-florido,ferroviario,jequitiba,mineracao,pedra-branca,rio-turvo,serra-negra"
python -m manager_core season --ruleset test-liga-unica --participants $liga outcomes
python -m manager_core season rules --validate core/tests/fixtures/rulesets/R004_groups_vs_participants.toml
```

Expected: the test ruleset plays a full season, and the broken file exits 1 with R004 explained.
The Liga Única takes 8 clubs, so they are named with `--participants` (by default a season takes
every club of the ruleset's state, and the sample world has 12).

## 6. The year (US4)

```powershell
python -m manager_core season calendar
python -m manager_core season calendar --month 2
```

Expected: a month-by-month summary of the whole year, with reserved windows labelled. February
shows each day's Mineiro matches.
