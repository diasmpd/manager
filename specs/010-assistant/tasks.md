# Tasks: The Assistant's Suggestions

**Input**: [spec.md](spec.md). Tests first (Constitution IV), on the fictional sample.

## Foundational

- [x] T001 Thresholds in core/src/manager_core/reference/career/assistant.toml (better-on-bench
  margin, role suitability gain, strength bands, cover needs per line, ageing and youth ages).
- [x] T002 The data shapes: `Advice` (kind, severity, text, action), `OppositionReport`,
  `Briefing`. In core/src/manager_core/career/assistant.py.

## User Story 1 - Know the opponent (P1)

- [x] T003 Tests: the report's opponent, style, formation, strength band, key players, scorers
  and form as of a day, suspensions, the first-round case. In core/tests/unit/test_assistant.py.
- [x] T004 Implement `opposition_report(career, match_id, as_of)`.

## User Story 2 - Selection warnings (P1)

- [x] T005 Tests: one yellow from a ban; out of position with a natural swap; better on the
  bench; applying the swap makes a valid selection and the warning goes.
- [x] T006 Implement `selection_advice(career, selection)`.

## User Story 3 - Tactic advice (P2)

- [x] T007 Tests: a big underdog away gets the AI's adaptation (and an even match none); a badly
  suited role gets a better one; every action yields a valid tactic.
- [x] T008 Implement `tactic_advice(career, tactic, match_id)`.

## User Story 4 - Squad advice (P3)

- [x] T009 Tests: a line without cover, an ageing regular, a youngster ready.
- [x] T010 Implement `squad_advice(career)`.

## Delivery

- [x] T011 `api.assistant_briefing`, and the `assistant` news items (FR-006) in
  career/views.py, with tests (dated the day before; as-of form; one squad item per season;
  deterministic).
- [x] T012 Server `assistant.briefing`, contract 1.3, and a contract test.
- [x] T013 Client: the "Assistente" panel on team selection (report, then the advice, with
  "Aplicar" sending the action through the existing methods), and a client test.
- [x] T014 SC-002 check over several careers; README, roadmap; both suites, ruff and mypy; PR.

## Progress notes (2026-10-21)

- The opposition report, selection, tactic and squad advice are built and tested on the sample
  (15 unit tests, 2 contract tests, the client's briefing check).
- Design call: "youngster ready" compares with the owner's XI's median starter (the first
  rule, "as good as the weakest starter at his position", could never fire against the
  assistant's own XI, which would already have picked him).
- `assistant.briefing` takes the selection on screen: on main the screen keeps its edits until
  Confirmar e jogar, so the briefing must advise on what the owner sees.
- Not checked visually yet: the panel's layout in the window (no screenshot run while the PC
  was in use). For the owner's first look.
