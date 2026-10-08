# Data Model: Real Data for Minas Gerais Clubs

The game dataset keeps the **001 format** (clubs, players, attributes, positions, squads, sources,
external refs, record flags). 011 adds no new game table. It fills the existing ones from real
sources, and adds the inputs and outputs of the pipeline in the private repository.

## In the game dataset (001 format, private copy)

| File | 011 use |
|---|---|
| `dataset.csv` | `fictional=false`, `tool=manager_core.realdata`, `tool_version`, `reference_date` (the squads' date). |
| `clubs.csv` | Real identity, city and state, stadium and capacity, founding year, `color_primary` and `color_secondary` (`#RRGGBB`, validated), and reputation (from the club baseline, R4). |
| `players.csv` | `player_id = p-og<ogol id>`. Also full and display name, birth date, nationality, height, feet, potential ability (R4). |
| `attributes.csv` | The synthesis model's 1–20 attributes. |
| `positions.csv` | Positions with familiarity: the listed position is natural, others come from the profile. |
| `squads.csv` | Club, shirt number, market value (EUR, when known). |
| `sources.csv` | One row per source: name, URL, retrieval date, licence note (e.g. "ogol: no published terms; private use only, owner decision 2026-10-07"). |
| `external_refs.csv` | `(record_type, record_id, source, source_id)`: each record's ogol and Wikipedia ids. |
| `record_flags.csv` | `synthesis_confidence` (`high`, `medium` or `low`, with the reason), `manually_edited` (from corrections), `incomplete` (a missing field, with the reason). |

## Pipeline entities (private repository)

### ClubInput (`inputs/mineiro.toml`)
- `club_id`: the slug;
- `division`: Série A, B, C, D or none;
- `module`: I or II;
- `ogol_id`, `wikipedia_title`;
- `colors`: the owner's two colours, when the sources lack text colours;
- `stadium` and other overrides: optional.

**Validation**: every Módulo I club is present, its ids are non-empty, and colours are
`#RRGGBB`.

### CachedPage (`cache/<source>/<hash>.html.gz` plus `cache/<source>/log.csv`)
- `url`, `fetched_at`, `status`, `bytes`.
- A page is fetched once and re-read from the cache until `--refresh`.

### RawClub / RawPlayer (in memory, from the parsers)
- **RawClub**: what one source said: name, city, stadium, capacity, founded, colours (if text), and
  its squad's player ids and shirt numbers.
- **RawPlayer**: name, birth date or age, nationality, position, height, foot, games, minutes,
  goals, assists, market value, and the source id.

### Correction (`corrections.csv`, append-only)
- Columns: `record_type`, `record_id`, `field`, `old_value`, `new_value`, `date`, `note`.

**Rules**:
- applied last, owner values win;
- kept across imports;
- reported when the source value under it changed, or when the record is gone.

### ImportRun (`datasets/<name>/import-report.md`)
- Its inputs: cache date range, model version, number of corrections.
- Per club: players found, fields missing, source disagreements, unresolved identities, the
  confidence mix.
- SC-003: the club strength ranking against the real table, with its Spearman correlation.

## State: a player through the pipeline

```text
fetched (cache) → parsed (RawPlayer) → merged (identity + precedence) → synthesised (CA,
attributes, PA, confidence) → corrected (owner values) → written (dataset) → validated (001)
```
