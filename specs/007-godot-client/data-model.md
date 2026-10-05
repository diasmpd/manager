# Data Model: Godot Desktop Client

The client adds no game data. Every game entity (careers, selections, tactics, matches, tables,
players) is the core's, and travels as JSON results ([contracts/local-api.md](contracts/local-api.md)).
This file describes what the client and the server hold themselves.

## Server session (core side, `manager_core.server`)

| Field | Meaning |
|---|---|
| `saves` | the saves folder given at start |
| `career` | the open `Career`, or none until `career.new` or `career.open` |
| `dataset` | the sample world, loaded lazily for `career.clubs` and `career.new` |

**Rules**:
- a method needing a career fails with `P004` when none is open;
- `career.open` and `career.new` replace the open career (the previous one is saved first);
- one request at a time.

## Client session (Godot side, the `Core` autoload)

| Field | Meaning |
|---|---|
| `state` | `starting` → `ready` ⇄ `busy` → `closed` / `failed` |
| `pid`, `pipe` | the core process and its stdio |
| `next_id` | the next request id |
| `pending` | request id → waiter (a signal the caller awaits) |
| `contract` | the version the core returned in `hello` |
| `strings` | the `ui.*` strings from `hello` |

**State transitions**:
- `starting` → `ready`: the process started and `hello` returned a compatible major version.
- `starting` → `failed`:
  - the process failed to start (message: Python not found);
  - `hello` timed out;
  - the major versions differ (message names both).
- `ready` → `busy` while requests are pending; `busy` → `ready` when none are left.
- any state → `failed` if the process stops unexpectedly. The window shows the message and
  offers to restart.
- `closed` after `shutdown` returns, or when the window closes (then the process is killed,
  after a short grace period).

## Screens (client side)

Each screen asks `Core` and draws the answer. It holds only what it is editing:
- **team selection**: the working `Selection`, until it is confirmed;
- **tactics**: the working `Tactic`, until it is confirmed;
- **calendar**: the month shown;
- **tables**: the group shown;
- **match day**: the feed position and the speed.
