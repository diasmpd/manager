# Manager

A personal football management game for Windows. Football Manager is the realism benchmark, and
the game is built around Brazilian football. The simulation core is in Python and the desktop
client is in Godot.

> Status: Milestone 0 in progress. Specs 001 (core domain model), 002 (competitions and
> calendar), 003 (quick sim), 004 (career save and game loop), 005 (playable season in the
> terminal) and 006 (tactics on the FM26 model, with AI club styles) are implemented. See [docs/roadmap.md](docs/roadmap.md).

## Quick start (Windows, PowerShell)

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "core[dev]"
python -m manager_core club list                        # the 12 fictional sample clubs
python -m manager_core club squad vale-do-ouro          # a squad
python -m manager_core player show p-000026             # an FM-style player profile
python -m manager_core lineup suggest vale-do-ouro --formation 4-3-3
python -m manager_core data validate data/sample        # import validation report

# a Campeonato Mineiro season, played by the quick sim (spec 003)
python -m manager_core season groups                    # the draw
python -m manager_core season fixtures --club alvorada  # one club's dates
python -m manager_core season --date 2027-02-01 table   # overall classification on a date
python -m manager_core season bracket                   # semifinals, final, Troféu Inconfidência
python -m manager_core season outcomes                  # champion, relegated, final order
python -m manager_core season calendar --month 2        # February day by day
python -m manager_core season rules                     # bundled competition rulesets
python -m manager_core season match primeira-fase-r01-01 # a match report (stats, goals, cards)
python -m manager_core season scorers                   # top scorers
python -m manager_core calibrate                        # quick-sim calibration vs real data

# a career (saved in saves/, autosaved weekly)
python -m manager_core career new minha --club alvorada  # choose your club
python -m manager_core career continue minha            # play to the next stop
python -m manager_core career status minha              # date, next match, suspensions
python -m manager_core season --career minha table      # any season view, on the career
python -m manager_core career history minha             # past seasons
```

Checks: `cd core; ruff check .; mypy; pytest -q`; the desktop client:
`.\tools\godot\godot_console.exe --headless --path client -s res://tests/run_tests.gd`. Validation guides:
[001](specs/001-core-domain-model/quickstart.md),
[002](specs/002-competitions-calendar/quickstart.md),
[003](specs/003-quick-sim/quickstart.md),
[004](specs/004-career-save/quickstart.md),
[006](specs/006-tactics/quickstart.md).

## Play (desktop window, spec 007)

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "core[dev]"
.\tools\setup_client.ps1        # once: portable Godot 4.7.2 (checked) + a "Manager" desktop shortcut
```

Double-click **Manager** on the desktop. Open or create a career; **Continuar** (or Space)
advances, **X** opens the tactics, **Esc** goes back. Closing the window saves. Guide:
[specs/007-godot-client/quickstart.md](specs/007-godot-client/quickstart.md). The window talks to
the Python core through the versioned local API ([contracts/local-api.md](contracts/local-api.md)).

## Play (terminal)

```powershell
pip install -e "tui[dev]"
python -m manager_core career new minha --club alvorada   # create a career once
python -m manager_tui minha                               # play: Space = Continuar, Q = save and quit
```

Keys and screens: [specs/005-terminal-season/quickstart.md](specs/005-terminal-season/quickstart.md).
**X** opens the Tactics screen: formations, mentality, team instructions by phase, roles and
player instructions, set pieces ([specs/006-tactics/quickstart.md](specs/006-tactics/quickstart.md)).

## Docs
- [Product vision](docs/vision.md): what the game is and the decisions behind it
- [Roadmap](docs/roadmap.md): milestones, spec order and the pain-point log
- [Constitution](.specify/memory/constitution.md): non-negotiable engineering principles
- `specs/`: one folder per feature (Spec Kit: spec → plan → tasks)

## How we work
Development follows [GitHub Spec Kit](https://github.com/github/spec-kit). Each feature gets a
spec, a plan and tasks, then an implementation on its own branch, merged through a PR.

## Data
Real club and player data is **not** in this repository. It lives in a private data repo.
This repo only contains code and a fictional sample dataset.

## Layout
- `tui/`: the terminal game (Textual), which calls only the core facade
- `core/`: headless Python simulation core (`manager_core`): domain model, ratings, CSV I/O,
  competitions (rulesets as TOML data, season engine, calendar), quick sim and calibration, CLI
- `data/sample/`: committed fictional sample world (generated, deterministic)
- `specs/`, `docs/`, `.specify/`: specifications and project governance

## Prototype
`prototype/` holds the first throwaway match-engine experiment (minute-by-minute duels). It is
kept for reference only and is not part of the product.
