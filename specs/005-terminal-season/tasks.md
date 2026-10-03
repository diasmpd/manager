---
description: "Task list for 005 Playable Season in the Terminal"
---

# Tasks: Playable Season in the Terminal

**Tests**: REQUIRED (Constitution IV). Write the tests first and see them fail.

## Phase 1: Setup

- [ ] T001 Create `tui/pyproject.toml` (`manager-tui`: `manager-core`, `textual>=8.2,<9`; dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`), and `tui/src/manager_tui/{__init__,__main__,app}.py` with a skeleton app. Install it into `.venv`. Add a `tui` job to `.github/workflows/ci.yml`.
- [ ] T002 [P] Architecture test `tui/tests/test_architecture.py`: `manager_tui` modules import only `manager_core.api` and `manager_core.i18n` from the core.

## Phase 2: Foundational (core)

- [ ] T003 [P] Tests then `career/selection.py`:
  - `Selection`;
  - `propose(career, formation)`: the assistant's XI without suspended players;
  - `validate(career, selection)`, with errors `suspended`, `not_in_squad`, `duplicate`, `bench_too_long` and the warning `no_goalkeeper`;
  - `to_team_sheet`.

  A property test: a selection with a suspended player is never valid (SC-004).
- [ ] T004 Tests then quick-sim overrides: `QuickSimProvider.override(club_id, sheet)` makes the user's matches use the sheet. The report lineup must equal the selection (SC-002).
- [ ] T005 Tests then save format v2: a `selection` table, and a migration 1→2 tested by loading a v1 file written by 004's code path (simulated with `user_version = 1` and no table).
- [ ] T006 [P] Tests then `quicksim/feed.py` `match_feed(report)`: every goal, card and substitution once, in order, with the right running score; half-time and full-time lines.
- [ ] T007 [P] Tests then `career/news.py` `career_news(career)`: the draw, user results, suspensions, qualifications, titles, relegations and season reviews, newest first.
- [ ] T008 Facade: `propose_selection`, `validate_selection`, `confirm_selection`, `match_feed`, `career_news`, `squad_view` (stars, status, season stats) and `last_user_match`. Contract tests.

## Phase 3: US1 - Play a season (P1) 🎯 MVP

- [ ] T009 [P] [US1] Pilot test: open a new career → Continuar to the first user match → team selection opens → confirm → feed at instant speed → report → Continuar to the season end → season review → next season. The results equal a CLI-continued career.
- [ ] T010 [US1] Home screen, left menu, Continuar flow, saving on quit, the launcher (`python -m manager_tui [--saves] [CAREER]`), and a too-small-terminal message.

## Phase 4: US2 - Pick the team (P2)

- [ ] T011 [P] [US2] Pilot tests: swap a starter with a bench player; change the formation; a suspended player is refused with its reason; a keeper-less XI warns; the report lineup equals the confirmed selection.
- [ ] T012 [US2] Team selection screen: pitch-style list by slot, bench and squad, swap with keys, formation picker, "assistant pick" and confirm.

## Phase 5: US3 - Match day (P3)

- [ ] T013 [P] [US3] Pilot tests: the feed shows every report event in order with the score; speed changes do not change content; instant speed jumps to the report.
- [ ] T014 [US3] Match day screen: the feed with speed control, then the report panel (003's view).

## Phase 6: US4 - Squad, tables, calendar, news (P4)

- [ ] T015 [P] [US4] Render tests at 100×30 for each screen at the season start, middle and end; the player profile hides hidden attributes; a news item for a suspension.
- [ ] T016 [US4] Squad (and profile), Tables/Fixtures (groups, overall, bracket, fixtures, match report), Calendar and News screens.

## Phase 7: Polish

- [ ] T017 [P] README (how to play), roadmap (005 done, 006 next), quickstart.
- [ ] T018 Full core and tui suites, ruff and mypy; manual run in Windows Terminal; then the PR.
