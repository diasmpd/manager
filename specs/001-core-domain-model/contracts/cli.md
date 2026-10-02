# Contract: CLI (001)

Invocation: `python -m manager_core <group> <command> [options]`. Output text is pt-BR via the
i18n layer. Every command calls only the facade ([facade.md](facade.md)).

Global option: `--data <dir>` selects the dataset folder (default: the repo's `data/sample/`).

Exit codes: `0` success; `1` validation errors (report printed); `2` usage error;
`3` not found (unknown club, player or formation).

| Command | Purpose | Output |
|---|---|---|
| `data validate <dir>` | Validate a dataset without loading it | Report: errors and warnings grouped by file, plus a summary line. Exit 1 if there are errors |
| `data export <src_dir> <dst_dir>` | Load (must validate) and export canonically | Summary of records written, plus flags raised (e.g. manually_edited) |
| `sample generate [--seed N] [--out DIR]` | Regenerate the fictional world | Summary. Defaults: seed 20261002, out `data/sample/` |
| `club list` | All clubs | Table: id, name, abbreviation, city/UF, reputation, squad size, average CA |
| `club squad <club_id> [--sort position\|ca\|age\|number]` | A club's squad | Table: number, display name, age, best position, familiarity band, suitability, CA |
| `player show <player_id> [--hidden]` | Full profile | Identity block, positions with bands, attributes grouped FM-style (hidden only with `--hidden`), CA/PA (PA only with `--hidden`) |
| `position rank <club_id> <POS>` | Who can play a position | Ranked table: display name, familiarity band, suitability |
| `lineup suggest <club_id> [--formation 4-4-2]` | Best XI | Slot-by-slot table: slot position, player, suitability, total, flags |
| `formation list` | Available formations | Names and their 11 positions |

Duplicate display names in one table are disambiguated with the shirt number or birth year
(edge case "two Gabriels").
