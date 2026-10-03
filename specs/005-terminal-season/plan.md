# Implementation Plan: Playable Season in the Terminal

**Branch**: `005-terminal-season` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

## Summary

A Textual terminal UI, in its own package `tui/`, puts Milestone 0's playable season on screen.
It has these screens:
- Home with Continuar;
- Team selection (the assistant's proposal, which the owner can edit);
- Match day (a live text feed, then the report);
- Squad (with player profiles);
- Tables and fixtures;
- Calendar;
- News.

The core gains everything the UI needs, with no rules in the UI:
- the user's **selection**, saved with the career (save format v2);
- a quick-sim override so the user's matches use that selection;
- facade views for the **feed**, **news**, **squad stats** and **stars**.

Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.12

**Primary Dependencies**:
- core: none added;
- tui: `textual>=8.2,<9` (justified in R1);
- dev: `pytest-asyncio` for the UI tests.

**Storage**: save format v2, which adds the `selection` table, with a migration from v1.

**Testing**:
- core unit and contract tests for selection, feed and news;
- tui pilot tests (scripted sessions) and render tests at 100×30.

**Target Platform**: Windows Terminal and the classic Windows console (CI on Windows only).

**Performance Goals**:
- screen switches under 0.5 s (SC-005);
- a scripted full season under 60 s (SC-001).

**Constraints**:
- The UI calls only `manager_core.api` (Constitution III, enforced by an import-check test).
- Every string goes through i18n (pt-BR).

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ (n/a) | No simulation change. A selection override leaves the quick sim and its calibration as they are. |
| II. Determinism | ✅ | The selection is a recorded user decision, and the same selection and seed give the same match. The feed speed never affects results. |
| III. Headless core, thin client | ✅ | Rules (validation, proposal, feed, news) are in the core facade. A test fails if `manager_tui` imports anything but `manager_core.api` and the i18n `t`. |
| IV. Test-first | ✅ | Core tests come before code. UI pilot tests come before the screens. |
| V. Smart automation | ✅ | The assistant proposes the XI, and it is a suggestion the owner edits (Principle V: suggestions by default). |
| VI. Data rights | ✅ | The UI shows the sample world. No new data. |
| VII. Incremental | ✅ | No tactics (006), in-match changes or saves screen (owner). |
| Tech constraints | ✅ / justified | New dependency: Textual, for the TUI only (R1). |

## Project Structure

```text
core/src/manager_core/
├── career/selection.py   # Selection, propose, validate, to TeamSheet
├── career/news.py        # NewsItem derivation
├── quicksim/feed.py      # FeedLine from a MatchReport
├── quicksim/provider.py  # per-club sheet overrides
├── career/store.py       # format v2 + migration 1->2
├── api.py                # propose/validate/confirm selection, play_user_match, match_feed,
│                         # career_news, squad_view
└── i18n/pt_BR.py         # UI strings
tui/
├── pyproject.toml        # manager-tui: manager-core, textual
├── src/manager_tui/__init__.py, __main__.py, app.py, screens/*.py, widgets/*.py, app.tcss
└── tests/                # pilot + render tests, architecture (imports) test
.github/workflows/ci.yml  # + tui job
```

## Complexity Tracking

| Item | Why | Simpler alternative rejected because |
|---|---|---|
| New dependency (Textual) | The owner chose a full-screen TUI | curses has no native Windows support. Hand-rolled ANSI would be far more code and untestable. |
