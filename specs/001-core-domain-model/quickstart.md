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
monotonicity (property test), best-XI optimality (SC-006), sample determinism (SC-002) and
attribute coherence (SC-005).

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

## 4. Validation errors (User Story 2)

```powershell
python -m manager_core data validate core/tests/fixtures/invalid/E004_attribute_out_of_range
```

Expected: exit code 1. The report names `attributes.csv`, the player id, the field and the
1–20 range, in pt-BR.

## 5. Who can play where, and the best XI (User Story 3)

```powershell
python -m manager_core position rank <club_id> DC
python -m manager_core lineup suggest <club_id> --formation 4-3-3
```

Expected: natural DCs on top, and an XI with one goalkeeper and no repeated player.

## 6. Excel round-trip by hand (User Story 4, SC-008)

1. `python -m manager_core data export data/sample $env:TEMP\edit-me`
2. Open `$env:TEMP\edit-me\attributes.csv` in Excel by double-clicking it. Columns should split
   correctly. Change one player's `finishing`, then save (keep the CSV format).
3. `python -m manager_core data export $env:TEMP\edit-me $env:TEMP\edited`

Expected: the import succeeds, the summary reports exactly one `manually_edited` player, and
`git diff --no-index` between `edit-me` and `edited` shows only that value (plus integrity and
flags). Do it in under 5 minutes.
