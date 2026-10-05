# Data Model: Positional Match Engine

## Match state (in memory, `positional/state.py`)

| Entity | Fields |
|---|---|
| **Pitch** | 105 × 68 m. Origin at the home goal line, left touchline. x is towards the away goal, y across. |
| **Ball** | position (x, y), height z, velocity, owner (a player id or none), state (in play / dead), restart (kick-off, throw-in, goal kick, corner, free kick, penalty) |
| **PlayerState** | id, side, slot, position, velocity, target, energy (0–1), yellow card, sent off, on the pitch, distance run, sprint distance |
| **Team** | side, the tactic (006 `Tactic`), current formations, intents (chase / protect / level / relaxed), substitutions made and windows used, players on the pitch, bench |
| **Clock** | time in seconds, half, stoppage time, the next restart |

**Invariants**:
- At most 11 players per side on the pitch.
- A sent-off player never returns.
- A substituted player never returns.
- The ball has at most one owner.

## Match decision (recorded, `positional/engine.py`)

| Field | Meaning |
|---|---|
| `at` | match time in seconds (when the owner paused) |
| `kind` | `substitution` or `tactic` |
| `side` | home or away (the user's side) |
| `payload` | substitution: off, on and slot; tactic: the full 006 `Tactic` |

**Rules**:
- Decisions are applied in time order, before the step at time `at`.
- **Substitutions** must respect the ruleset (5 changes, 3 windows plus half-time). The player
  coming off must be on the pitch, and the one coming on must be on the bench and eligible.
- **A tactic** must pass 006 validation for the current players.

## Live match (server session)

| Field | Meaning |
|---|---|
| `match_id`, `seed` | the user's pending match, and its seed |
| `engine` | the `LiveMatch` being stepped |
| `decisions` | the decisions so far |
| `feed_cursor` | the feed lines already sent |

**States**:
- `none` → `playing` (`match.start`);
- `playing` → `playing` (`match.advance`, `match.substitute`, `match.tactic`);
- `playing` → `finished` (full time reached, or `match.finish`);
- `finished` → `none` (the result is committed and the match day continues).

## Positional record (stored, `positional/record.py`)

| Field | Meaning |
|---|---|
| `match_id` | the user's match |
| `hz` | 2 |
| `players` | the player ids and their sides, in sample order |
| `samples` | for each sample: the ball (x, y, z in cm) and 22 (x, y) in cm, int16; a player not on the pitch is (−1, −1) |
| `events` | (sample index, event index into the match report) |

Stored zlib-compressed in the SQLite table `records(match_id TEXT PRIMARY KEY, blob BLOB)`, save
format v4.

## Parameters (`reference/positional/model.toml`)

Groups:
- `movement`: top speed and acceleration from pace and acceleration, and turning;
- `shape`: line heights, width and compactness for each instruction setting, and role offsets;
- `decide`: option weights, noise by decisions and composure, pressure radius;
- `duel`: tackle, dribble, foul and card;
- `xg`: logistic coefficients;
- `keeper`;
- `energy`;
- `intents`: chase, protect, level and relaxed;
- `set_pieces`.

Every value is data, and the positional tuner fits them.
