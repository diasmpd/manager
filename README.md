# Manager

A personal football management game for Windows. Football Manager is the realism benchmark, and
the game is built around Brazilian football. The simulation core is in Python and the desktop
client is in Godot.

> Status: Milestone 0 in progress. Spec 001 (core domain model) is implemented. See
> [docs/roadmap.md](docs/roadmap.md).

## Quick start (Windows, PowerShell)

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e "core[dev]"
python -m manager_core club list                        # the 12 fictional sample clubs
python -m manager_core club squad vale-do-ouro          # a squad
python -m manager_core player show p-000026             # an FM-style player profile
python -m manager_core lineup suggest vale-do-ouro --formation 4-3-3
python -m manager_core data validate data/sample        # import validation report
```

Checks: `cd core; ruff check .; mypy; pytest -q`. The full validation guide is
[specs/001-core-domain-model/quickstart.md](specs/001-core-domain-model/quickstart.md).

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
- `core/`: headless Python simulation core (`manager_core`): domain model, ratings, CSV I/O, CLI
- `data/sample/`: committed fictional sample world (generated, deterministic)
- `specs/`, `docs/`, `.specify/`: specifications and project governance

## Prototype
`prototype/` holds the first throwaway match-engine experiment (minute-by-minute duels). It is
kept for reference only and is not part of the product.
