---
description: "Task list for 004 Career Save and Game Loop"
---

# Tasks: Career Save and Game Loop

**Input**: Design documents from `specs/004-career-save/`

**Tests**: REQUIRED (Constitution IV). Write the tests first and see them fail.

**Paths**: the package is `core/src/manager_core/`; tests are in `core/tests/`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create `core/src/manager_core/career/__init__.py` and `reference/career/__init__.py`, add `reference/career/*.toml` to the package data in `core/pyproject.toml`, and add `saves/` to `.gitignore`.

## Phase 2: Foundational

- [X] T002 [P] Test then refactor `sample/generator.py`: expose `make_player(rng, pid, position, quality, reference_date, age=None)` and `make_club(...)`. `generate()` output must stay byte-identical: 001's sample determinism tests guard it, plus a new test comparing the CSV export hash.
- [X] T003 [P] Codec tests `tests/unit/test_career_codec.py`: `Result`, `MatchReport` (all event kinds, shootouts, lineups, keepers) and `SeasonRecord` round-trip to JSON and back, equal to the original. Use hypothesis over simulated matches. Then implement `career/codec.py`.
- [X] T004 Add `MatchContext.unavailable` (002) and the season's discipline hook. Make the quick sim provider build sheets without unavailable players, cached per (club, frozenset). Tests: an unavailable player never appears in the report; the sheet cache returns the same object for the same set; 002 and 003 suites stay green.
- [X] T005 [P] Write `reference/career/development.toml`, `retirement.toml` and `promoted-clubs.toml` per research R8, R9 and R7, with i18n strings for career stops, statuses, history and V-codes.

## Phase 3: US1 - Start a career and save it (P1) 🎯 MVP

- [X] T006 [P] [US1] Tests `tests/integration/test_career_save.py`:
  - `new_career` writes a save whose `load` equals the career (every 002 view);
  - `save --as` gives an independent copy;
  - `user_version` 2 is refused with `V001`;
  - a stored result for an unknown match id gives `V003`;
  - an atomic-write failure (patch `os.replace` to raise) leaves the old file loadable (SC-006).
- [X] T007 [US1] Implement `career/store.py` (SQLite schema, atomic write, versions and migrations hook, V-codes), `career/recorded.py` (`RecordedProvider`) and `career/career.py` (`Career`, `new_career`).
- [X] T008 [US1] Facade and CLI: `new_career`, `load_career`, `save_career`, `list_saves`, `delete_save`, `career_status`; `career new|list|status|save|delete`; and `season --career NAME` for all 002 and 003 views. Contract test `tests/contract/test_cli_career.py`.

## Phase 4: US2 - Continue day by day (P2)

- [X] T009 [P] [US2] Tests `tests/integration/test_career_loop.py`:
  - the first continue stops the day before the user's first match;
  - the next one plays it;
  - every stop is a user match day ahead, a competition event or the season end;
  - no user match is passed without a stop before it;
  - weekly autosave (the file appears and its date advances by 7 or more days);
  - SC-001: save and load at 50 random stops, then continue both to the season end with identical results;
  - SC-002 timing (`slow`).
- [X] T010 [US2] Implement `continue_` (stops, autosave) and the `career continue [--to-season-end]` CLI.

## Phase 5: US3 - Suspensions (P3)

- [X] T011 [P] [US3] Tests `tests/unit/test_discipline.py`:
  - hand-built report sequences give a red → one match;
  - a third yellow → one match and a reset;
  - a second yellow counts toward the red only;
  - a ban carries into a two-legged tie's second leg;
  - the ledger is empty at season start.

  Also an integration test over 100 seasons: no suspended player appears; every ban is served exactly once (SC-003).
- [X] T012 [US3] Implement `career/discipline.py` and wire it into the season hook. Show suspensions in `career status`.

## Phase 6: US4 - The next season (P4)

- [X] T013 [P] [US4] Tests `tests/integration/test_rollover.py`:
  - after a season: 12 participants, the relegated clubs gone, 2 promoted clubs with full squads;
  - every squad back to 27;
  - every player a year older;
  - development: the mean ΔCA of 18–21-year-olds is > 0 and of 33+ is < 0;
  - nobody under 30 retires;
  - the rollover is deterministic.

  A `slow` 10-season test checks SC-004 (mean squad age 24–28) and SC-005 (median retirement age 34–36).
- [X] T014 [US4] Implement `career/rollover.py` and the season-end stop → rollover on the next continue, plus `career history`.

## Phase 7: Polish

- [X] T015 [P] Update `docs/roadmap.md` (004 done, 005 next) and the README quick start (`career` commands).
- [ ] T016 Make sure ruff, mypy (strict) and the full suite pass, run the quickstart on Windows, and open the PR.

## Dependencies

Setup → Foundational → US1 → US2 → US3 → US4 → Polish. US3 needs the loop (US2) to exercise
bans across matches. US4 needs saves and the loop.
