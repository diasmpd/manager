# Feature Specification: Choose the World for a New Career

**Feature Branch**: `013-world-choice`

**Created**: 2026-10-19

**Status**: Draft

**Input**: Owner question (2026-10-19): "Anything that can be worked on while the positional engine
is running?" The answer chosen: play with the real clubs. Spec 011 builds a real Mineiro dataset
in the private `manager-data` repository, but the desktop game always starts careers in the
fictional sample world, because the client never tells the core about another dataset.

Milestone 0 (the playable prototype, "using a fictional or sample dataset and, once collected,
real MG club data").

## Context

**FM is the benchmark.** Football Manager asks for the database when a new game starts (FM's
"Database" choice on the new-career screen); the database then belongs to that save, and loading
a save never asks again. We do the same with a "world": the fictional sample, or a real dataset
built by spec 011.

What already exists:
- the core loads any 001 dataset (`api.load_dataset`), and a career save already embeds the whole
  world it was started in (spec 004), so a save never depends on the dataset folder again;
- the local server takes one `--data` folder (spec 007), and the client never passes it.

Data rights (Principle VI): the public repository only learns *where* the private repository is
(a relative path in `client/core.cfg`); no real data is committed. When the private repository is
not there, the game offers the sample alone, exactly as today.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a career with the real clubs (Priority: P1)

On the new-career form, the owner picks the world (the fictional sample, or "mineiro-2026", built
from real data), then a club of that world, and plays.

**Independent Test**: with a data repository holding one built dataset, the new-career form
offers two worlds; choosing the real one lists its clubs, and the career starts in it.

**Acceptance Scenarios**:

1. **Given** a data repository with built datasets, **When** the new-career form opens, **Then**
   it offers the sample first, then each dataset, with its number of clubs and players.
2. **Given** a world chosen, **When** the club list is shown, **Then** it lists that world's clubs.
3. **Given** a career started in a real world, **When** it is saved and opened again, **Then** it
   plays in that world (the save embeds it), whatever the data folder holds by then.

### User Story 2 - Nothing changes without the private data (Priority: P1)

**Independent Test**: with no data repository (or an empty one), the form looks and works as in
spec 007: no world choice is shown, and careers start in the sample.

**Acceptance Scenarios**:

1. **Given** no data repository, **When** the form opens, **Then** no world choice is shown.
2. **Given** a dataset folder that does not validate, **When** the worlds are listed, **Then** it
   is left out (the form never offers a world that cannot start a career).

## Requirements *(mandatory)*

- **FR-001**: The core lists the worlds: the sample (always first), then each folder under
  `<data repository>/datasets/` holding a valid 001 dataset, in name order.
- **FR-002**: Each world carries an id, a PT-BR label, whether it is fictional, its club and
  player counts and its reference date.
- **FR-003**: `career.clubs` and `career.new` take an optional world id; without it they use the
  sample (contract 1.1 clients keep working). An unknown world is a NOT_FOUND error.
- **FR-004**: The client passes the data repository to the core from `client/core.cfg`
  (`data_repo`, relative to the repository root), overridable by `MANAGER_DATA_REPO` (tests), and
  only when the folder exists.
- **FR-005**: The new-career form shows the world choice only when there is more than one world.
- **FR-006**: No rule lives in the client (Principle III): the list, the labels and validation
  are the core's.

## Success Criteria *(mandatory)*

- **SC-001**: The owner starts a Cruzeiro career in the real Mineiro from the desktop window.
- **SC-002**: With no private repository, every spec 007 client test passes unchanged.
- **SC-003**: Contract tests cover the world list (sample only; sample plus datasets; an invalid
  folder left out), clubs and career creation per world, and the unknown-world error. They use
  fictional data only.

## Out of scope

- Choosing among rulesets or competitions (Milestone 1).
- Building or refreshing datasets from the game (spec 011's CLI does it).
- Showing a save's world in the careers list.
