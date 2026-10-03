# Contract: Save File Format v1 (SQLite)

One file per save: `<saves>/<name>.sqlite`. The autosave slot is `<saves>/autosave.sqlite`.
Names are slugs (`[a-z0-9-]{1,40}`), and `autosave` is reserved.

`PRAGMA user_version = 1` holds the format version.

| Table | Columns | Rows |
|---|---|---|
| `meta` | `key TEXT PRIMARY KEY, value TEXT` | `core_version`, `python_version`, `created_at`, `saved_at` (ISO timestamps, display only) |
| `career` | `name, master_seed INTEGER, user_club_id, current_date, last_autosave, pending_json` | exactly 1 |
| `world_files` | `name TEXT PRIMARY KEY, text TEXT` | the canonical 001 CSV files of the world at the start of the current season |
| `season` | `ruleset_toml, year INTEGER, master_seed INTEGER, participants_json` | exactly 1 |
| `results` | `match_id TEXT PRIMARY KEY, result_json TEXT` | one per played match of the current season |
| `history` | `year INTEGER PRIMARY KEY, record_json TEXT` | one per finished season |

**Loading**:
- **Version check**: `user_version` greater than 1 is refused with error `V001`. A smaller
  value runs the migrations in order; a missing migration gives `V002`.
- **Rebuild**: the world is read through 001's reader, which must validate. The season is
  rebuilt with `Season.start` from `season`. It is replayed to `career.current_date` with the
  stored results (`RecordedProvider`).
- **Mismatch**: a stored result for a match id that does not exist in the rebuilt season is an
  error (`V003`, corrupt save).

**Writing**: write to `<name>.sqlite.tmp`, commit and close, then `os.replace` it over the
target. The previous file stays loadable if the write fails (SC-006).
