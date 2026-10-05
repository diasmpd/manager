# Tasks: Godot Desktop Client

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[contracts/local-api.md](../../contracts/local-api.md), [data-model.md](data-model.md)

**Tests**: required (Constitution IV). Contract tests come before each server method group, and
scene tests before each screen.

## Phase 1: Setup

- [ ] T001 Create `core/src/manager_core/server/` (`__init__.py`, `__main__.py`, `protocol.py`, `encode.py`, `methods.py`) and `client/` with `project.godot` (Godot 4.7, window 1280×720 minimum, `Core` autoload). Add `tools/godot/` to `.gitignore`.
- [ ] T002 Write `tools/setup_client.ps1`. It downloads `Godot_v4.7.2-stable_win64.exe.zip` from the official release into `tools/godot/`, checks it against the release's `SHA512-SUMS.txt`, extracts `godot.exe`, and creates the desktop shortcut "Manager" (target: `godot.exe --path <repo>\client`). It is idempotent.

## Phase 2: Foundational (the contract)

- [ ] T003 Tests then `server/encode.py`. Dataclass → object, Enum → value, date → ISO, tuple → array, nested structures and None. Plus the reverse decoders the methods need: `Selection` and `Tactic` from JSON.
- [ ] T004 Tests then `server/protocol.py`:
  - one JSON object per line on stdin/stdout, with stdout reserved for messages;
  - dispatch by method name;
  - errors P001–P005 and NOT_FOUND;
  - the domain errors SELECTION, TACTIC and SAVE, each with `data`;
  - `progress` notifications;
  - one request at a time.
- [ ] T005 Tests then the session methods: `hello` (contract `1.0`, core and model versions, every `ui.*` string) and `shutdown` (saves the open career, then exits). `__main__` takes `--saves`.

## Phase 3: US4 + US1 - Careers and the season loop, core side (P1)

- [ ] T006 [US4] Tests then `career.list`, `career.clubs`, `career.new`, `career.open` (with notices), `career.save` and `career.status`; P004 when no career is open.
- [ ] T007 [US1] Tests then `career.continue`, including `to_season_end` with `progress` notifications; and `view.home` (a new facade helper: status, last match, latest 5 news items).
- [ ] T008 [US1] Parity test: a season through the server (confirming the current selection at each user match) equals the same career through the facade (SC-002).

## Phase 4: US2 - Selection and tactics, core side (P1)

- [ ] T009 [US2] Tests then `selection.current`, `selection.propose`, `selection.swap`, `selection.validate`, `selection.confirm` (with `tactic_changes`) and `formations.list`.
- [ ] T010 [US2] Tests then `tactic.options`, `tactic.current`, `tactic.default`, `tactic.suggest_oop`, `tactic.roles`, `tactic.suitability` (in a batch), `tactic.validate` and `tactic.confirm`.

## Phase 5: US3 - Views, core side (P2)

- [ ] T011 [US3] Tests then `view.squad`, `view.player`, `view.table`, `view.groups`, `view.fixtures`, `view.calendar`, `view.news`, `view.match` (feed, plus stat rows as data: a new facade helper) and `view.last_user_match`.

## Phase 6: Client foundation

- [ ] T012 `client/autoload/core.gd`:
  - reads `core.cfg`;
  - starts `pythonw.exe -m manager_core.server` with `OS.execute_with_pipe`, with a reader thread;
  - matches request ids to awaitable results, and handles errors;
  - `hello` with the major-version check;
  - detects a dead process and offers a restart;
  - `shutdown` on window close.

  Check by hand that no console window appears.
- [ ] T013 `client/tests/run_tests.gd`: a headless runner with no add-on dependency. Its first tests cover `Core` against the real server (the handshake, an unknown method's error, version refusal with a fake `hello`).
- [ ] T014 The `main` scene: the top bar (date, club, Continuar, busy indicator), the left menu, the content area and the shortcuts (Space, X, Esc). Labels come from the `hello` strings.

## Phase 7: Screens

- [ ] T015 [US4] The careers screen (list, open) and the new-career screen (name, club, the core's errors shown).
- [ ] T016 [US1] The home screen and the Continue flow (the stop kinds: user match → selection, event → news, season end → outcome).
- [ ] T017 [US2] The team selection screen: XI on the formation, bench and squad, swap, formation, assistant, confirm. Suspension refusal, the keeper warning, and the tactic-changes notice.
- [ ] T018 [US1] The match day screen: the live feed with speeds 1–4 and skip, then the stats.
- [ ] T019 [US2] The tactics screen: formations, mentality, instructions by phase, roles with suitability, player instructions with locks, set pieces, reset and confirm.
- [ ] T020 [US3] The squad and player screens.
- [ ] T021 [US3] The tables (groups, overall), fixtures, calendar (by month) and news screens.
- [ ] T022 Scene tests: each screen loads a canned result and draws it. Smoke test: open a career, continue once and close, against the real core.

## Phase 8: Polish

- [ ] T023 CI: on Windows, install Godot with `setup_client.ps1 -NoShortcut` (cached), then run the headless client tests.
- [ ] T024 Docs: README (the Play section for the desktop client); roadmap (007 is the Godot client, the positional engine becomes 008, and the rest shift); the quickstart parity checklist ticked; the contract file copied to `contracts/local-api.md` at the repo root.
- [ ] T025 Full suites (core, TUI, client), ruff and mypy, then the PR. Ask the owner before merging.

## Dependencies

- T001 → T003–T005 → (T006–T011, in any order) → T012 → T013, T014 → T015–T021 → T022 → T023–T025.
- The core methods (T006–T011) don't depend on the client. The client screens need only the methods they call.
