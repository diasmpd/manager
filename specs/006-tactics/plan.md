# Implementation Plan: Tactics

**Branch**: `006-tactics` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

## Summary

This spec adds FM26's tactics model as data and makes it matter in the quick sim.
- **Options as data**: formations (IP and OOP, with a larger catalogue), the 7-level
  mentality, all team instructions by phase, about 70 IP and OOP roles with key attributes and
  locked instructions, the 14 player instructions, and set pieces.
- **Effects**: each option moves a fixed set of quick-sim **levers** (shot rate, chance quality,
  allowed shots and quality, possession, fouls, cards, fatigue, set pieces, counters, errors).
  There are interaction rules between opposing settings, and role suitability scales player
  contributions.
- **AI**: AI clubs get styles from their squads and adapt before and during matches.
- **Checks**: the calibration gates run with AI styles on. A new exploit check bounds tactical
  advantage.
- **Terminal game**: the user's tactic is saved (format v3) and edited in a new Tactics screen.

Details: [research.md](research.md).

## Technical Context

- **Language**: Python ≥ 3.12, standard library only in the core (Textual stays in `tui/`).
- **Data**: `reference/tactics/{options,roles,effects,styles}.toml`, plus more OOP formations
  in `reference/formations.csv`.
- **Testing**:
  - option validation (T-codes);
  - effect direction and band tests per option;
  - role suitability;
  - AI style assignment and adaptation;
  - the exploit check in the PR gate;
  - save v3;
  - TUI pilot tests.
- **Performance**: levers are computed once per side per match, and when the state changes.
  The full season stays under 3 s.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Realism measured | ✅ | Gates run with AI styles on. Effect directions come from the analytics literature, and sizes are bounded and checked. The exploit check is in the PR gate. FM26 is the benchmark. |
| II. Determinism | ✅ | Styles and adaptation are deterministic (seeded manager profiles). Reports record the tactics. |
| III. Thin clients | ✅ | Validation, suggestions and suitability live in the facade, and the TUI only edits. |
| IV. Test-first | ✅ | Tests come before code throughout. |
| V. Smart automation | ✅ | The assistant suggests OOP shapes and default roles, and the owner decides. |
| VII. Incremental | ✅ | No positioning or editor (006b and 007), and no in-match user changes. |

## Project Structure

```text
core/src/manager_core/
├── tactics/
│   ├── model.py      # Tactic, SlotTactic, SetPieces, defaults, validation (T-codes)
│   ├── catalogue.py  # options, roles and styles loaders; OOP suggestions; role suitability
│   ├── effects.py    # Levers from (own tactic, opponent tactic, state)
│   └── ai.py         # style assignment, pre-match and in-match adaptation
├── reference/tactics/*.toml, reference/formations.csv (+ OOP shapes)
├── quicksim/engine.py, ratings.py, provider.py   # levers, role scaling, tactics per side
├── calibration/exploit.py, harness.py            # exploit check in the PR gate
├── career/store.py (format v3), api.py, i18n
tui/src/manager_tui/app.py                        # Tactics screen
```

## Complexity Tracking

No violations. This is the largest data spec so far, because the option set is FM's full one
(owner decision).
