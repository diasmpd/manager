# Manager

A personal football management game for Windows. Football Manager is the realism benchmark, and
the game is built around Brazilian football. The simulation core is in Python and the desktop
client is in Godot.

> Status: specification phase. See [docs/roadmap.md](docs/roadmap.md).

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

## Prototype
`prototype/` holds the first throwaway match-engine experiment (minute-by-minute duels). It is
kept for reference only and is not part of the product.
