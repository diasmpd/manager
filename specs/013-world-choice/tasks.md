# Tasks: Choose the World for a New Career

**Input**: [spec.md](spec.md). Small feature: the plan is the task list (one core module change,
one contract change, two client files).

**Tests**: required (Constitution IV), on fictional data only.

## Core and contract

- [x] T001 Write contract tests for the worlds (sample only; sample plus a dataset; an invalid
  folder left out; clubs and `career.new` per world; unknown world). In
  core/tests/integration/test_server_worlds.py.
- [x] T002 Implement `worlds.list` and the optional `world` of `career.clubs` and `career.new`,
  with `--data-repo` on the server. Contract 1.2. In core/src/manager_core/server/methods.py and
  __main__.py, contracts/local-api.md, and the PT-BR labels in i18n/pt_BR.py.

## Client

- [x] T003 Pass `--data-repo` from `core.cfg` (`data_repo`) or `MANAGER_DATA_REPO`, only when
  the folder exists. In client/autoload/core.gd and client/core.cfg.
- [x] T004 The new-career form: a world choice when there is more than one; changing it reloads
  the clubs; creation sends the world. In client/scenes/screens/careers.gd.
- [x] T005 Client test: the runner gives the core a temporary data repository holding a copy of
  the sample (the tests never see private data); two worlds are offered, the copy's clubs load,
  and the career starts in it, so every later spec 007 test runs unchanged on it. The sample-alone
  case is the core's contract test. In client/tests/run_tests.gd and test_screens.gd.

## Polish

- [x] T006 README (how to play the real Mineiro), roadmap, both suites, ruff and mypy, PR.
