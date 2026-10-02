# Quickstart: validating feature 001

These steps prove the feature end to end. Run them from the repo root in PowerShell.

## Setup

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "core[dev]"
```

## 1. Automated checks (all must pass)

```powershell
ruff check core; mypy core/src; pytest core/tests -q
```

The suite covers: validation fixtures (one per E-code, SC-004), round-trip (SC-003), CA
monotonicity (property test), best-XI optimality and tie determinism (SC-006), sample
determinism (SC-002) and attribute coherence (SC-005).

## 2. Explore the sample world (User Story 1)

```powershell
python -m manager_core club list
python -m manager_core club squad <club_id from the list> --sort position
python -m manager_core player show <player_id>            # visible attributes only
python -m manager_core player show <player_id> --hidden   # curator view
```

Expected: 12 clubs with 27 players each, and the strong-tier clubs have a clearly higher average
CA. Profiles read like FM's (groups, bands). Strikers finish better than centre-backs.

## 3. Determinism (SC-002)

```powershell
python -m manager_core sample generate --out $env:TEMP\sample-check
git diff --no-index --stat data/sample $env:TEMP\sample-check   # expected: no differences
```

## 4. Who can play where, and the best XI (User Story 2)

```powershell
python -m manager_core position rank <club_id> DC
python -m manager_core lineup suggest <club_id> --formation 4-3-3
```

Expected: natural DCs on top, and an XI with one goalkeeper and no repeated player.

## 5. Validation errors (User Story 3)

```powershell
python -m manager_core data validate core/tests/fixtures/invalid/E004_attribute_out_of_range
```

Expected: exit code 1. The report names `attributes.csv`, the player id, the field and the
1–20 range, in pt-BR.

## 6. Export round-trip (User Story 3, SC-003)

```powershell
python -m manager_core data export data/sample $env:TEMP\roundtrip
git diff --no-index --stat data/sample $env:TEMP\roundtrip   # expected: no differences
```

Optional: double-click `$env:TEMP\roundtrip\attributes.csv`. It must open in pt-BR Excel with
the columns split correctly. Don't save it from Excel: tolerating re-saved files is spec 011.
