# Data Model: Core Domain Model (001)

All domain objects are immutable (frozen dataclasses). "Range" means inclusive integer bounds.
Validation codes (`E…` errors, `W…` warnings) are defined in the catalogue at the end. The
CSV representation is in [contracts/csv-format.md](contracts/csv-format.md).

## Entities

### Club

| Field | Type | Rules |
|---|---|---|
| id | ClubId (slug) | unique in dataset (E003), slug pattern (E002) |
| name | str | required, 2–60 chars |
| short_name | str | required, ≤ 20 chars |
| abbreviation | str | exactly 3 uppercase letters A–Z (E020) |
| city | str | required |
| state | str \| None | UF code; required and valid when country = BRA (E021) |
| country | NationCode | FIFA trigram (E013 malformed / W006 unknown) |
| color_primary, color_secondary | str | `#RRGGBB` (E022) |
| stadium_name | str | required |
| stadium_capacity | int | 500–250,000 (E004) |
| founded_year | int | 1850–reference year (E004) |
| reputation | int | 1–20 (E004) |
| external_refs | tuple[ExternalRef, …] | optional |

### Player

| Field | Type | Rules |
|---|---|---|
| id | PlayerId (slug) | unique (E003), slug (E002) |
| full_name | str | required, 2–80 chars |
| display_name | str | required, ≤ 30 chars. Not unique: duplicates are disambiguated at display time |
| date_of_birth | date | valid date (E010); age at reference date 14–45 (E011) |
| nationalities | tuple[NationCode, …] | 1–3 entries, first = primary (E013 / W006) |
| height_cm | int | 150–210 (E004) |
| weight_kg | int | 50–110 (E004) |
| left_foot, right_foot | int | 1–20 (E004); max(left, right) ≥ 15 (E014) |
| attributes | Attributes | see below |
| positions | PositionFamiliarity | see below |
| potential_ability | int | 1–200 (E004); if below derived CA it is raised to CA, with the `potential_raised` flag (W010) |
| external_refs | tuple[ExternalRef, …] | optional |

**Derived (never stored)**:
- `age(reference_date)`.
- `current_ability()`: see research R8.
- `suitability(position)`: see R7.
- `best_position`: highest suitability among positions with familiarity ≥ 15. Ties are broken
  by FM position order.
- `is_goalkeeper`: best position is GK.

### Attributes (60 integers, each 1–20, E004)

FM order. Group membership is defined once in `ATTRIBUTE_GROUPS`.

- **Technical (14)**: corners, crossing, dribbling, finishing, first_touch, free_kick_taking,
  heading, long_shots, long_throws, marking, passing, penalty_taking, tackling, technique
- **Mental (14)**: aggression, anticipation, bravery, composure, concentration, decisions,
  determination, flair, leadership, off_the_ball, positioning, teamwork, vision, work_rate
- **Physical (8)**: acceleration, agility, balance, jumping_reach, natural_fitness, pace,
  stamina, strength
- **Goalkeeping (11)**: aerial_reach, command_of_area, communication, eccentricity, handling,
  kicking, one_on_ones, punching, reflexes, rushing_out, throwing
- **Hidden (13)**: adaptability, ambition, consistency, controversy, dirtiness,
  important_matches, injury_proneness, loyalty, pressure, professionalism, sportsmanship,
  temperament, versatility

**Hidden defaults when absent from the source**: 10, except dirtiness 8, injury_proneness 8 and
controversy 6. The record gets the `hidden_defaulted` flag.

**Display**: outfield players show Technical, Mental and Physical. Goalkeepers show Goalkeeping,
Mental, Physical and a reduced Technical set (first touch, free kicks, passing, penalty taking,
technique), as FM does. Hidden attributes appear only with `--hidden` (curator view).

### PositionFamiliarity

A mapping from each of the 14 `Position` codes to 1–20 (E004). Missing codes default to 1.

- At least one position must have familiarity ≥ 15 (E016).
- Bands (FR-011): Natural 18–20, Accomplished 15–17, Competent 12–14, Unconvincing 9–11,
  Awkward 5–8, Ineffectual 1–4.

`Position` enum (FM order): GK, DL, DC, DR, WBL, WBR, DM, ML, MC, MR, AML, AMC, AMR, ST.
Each position has a line (GK / DEF / MID / ATT): DEF = DL, DC, DR, WBL, WBR; MID = DM, ML, MC,
MR; ATT = AML, AMC, AMR, ST.

### SquadMembership

| Field | Type | Rules |
|---|---|---|
| player_id | PlayerId | must exist (E017); at most one membership per player (E018) |
| club_id | ClubId | must exist (E017) |
| shirt_number | int \| None | 1–99 (E004); unique per club (E019) |
| market_value | int \| None | ≥ 0 (E004) |
| wage_monthly | int \| None | ≥ 0 (E004) |
| currency | str \| None | ISO 4217 code (E023); required if a money field is set |
| contract_expiry | date \| None | valid date (E010) |

### Formation (reference data)

| Field | Type | Rules |
|---|---|---|
| name | str | unique (e.g. `4-4-2`) |
| slots | tuple[FormationSlot × 11] | exactly 11 slots, exactly one GK |

`FormationSlot`: index (0–10), position (Position), x_m (0–105), y_m (0–68), in the team's own
frame (x = own goal line → opponent's, y = left touchline).

### Dataset (aggregate root, `World` in code)

| Field | Type | Rules |
|---|---|---|
| format_version | str | supported (E030); a newer major version gets a clear refusal (E031) |
| reference_date | date | required (E010) |
| fictional | bool | required |
| tool, tool_version | str | required |
| seed | int \| None | required when produced by the generator |
| notes | str | optional |
| sources | tuple[Source, …] | ≥ 1 (E032) |
| clubs, players, memberships | collections keyed by id | iterated in sorted-id order (Constitution II) |
| record_flags | tuple[RecordFlag, …] | provenance flags per record |

`Source`: name, url (optional), retrieved_on (date), licence_notes (optional).
`ExternalRef`: source (str), source_id (str). The pair is unique per record type.
`RecordFlag`: record_type (club/player), record_id, flag ∈ {hidden_defaulted,
potential_defaulted, potential_raised}, detail. Flags persist across exports.
(`manually_edited` / `added_manually` are added by spec 011.)

**Queries** (pure functions over a Dataset):
- `squad(club_id)`
- `free_agents()`
- `rank_for_position(club_id, position)`
- `best_xi(club_id, formation)`: returns a `Lineup` (11 assignments plus flags such as
  `outfield_in_goal`). It is computed on integer scores `round(suitability × 1000)` with an exact
  tie-break (research R9).

### ValidationReport

`issues: list[Issue]`. Each `Issue` has: code, severity (error/warning), file, record_id or row
number, field, value, message (pt-BR via i18n). `ok` means zero errors. Issues are ordered by
file, then row, then field (deterministic).

## Validation catalogue

### Errors (block the import)

Codes are stable once published. Gaps (E006–E009, E012, E029) are reserved for future rules,
and retired codes are never reused. E026–E028 were added in the PR #1 review.

| Code | Rule |
|---|---|
| E001 | Required file missing (`dataset.csv`, `sources.csv`, `clubs.csv`, `players.csv`, `attributes.csv`, `positions.csv`) |
| E002 | ID doesn't match the slug pattern |
| E003 | Duplicate ID |
| E004 | Integer missing, non-integer or out of range |
| E005 | Required text field empty or too long |
| E010 | Invalid date |
| E011 | Age at reference date outside 14–45 |
| E013 | Malformed nation code |
| E014 | Neither foot ≥ 15 |
| E015 | *(retired: PA below CA is now W010, see below)* |
| E016 | No position with familiarity ≥ 15 |
| E017 | Reference to an unknown club or player |
| E018 | Player has more than one squad membership |
| E019 | Duplicate shirt number in a club |
| E020 | Abbreviation not 3 uppercase letters |
| E021 | Missing or invalid UF for a Brazilian club |
| E022 | Colour not `#RRGGBB` |
| E023 | Invalid or missing currency for money fields |
| E024 | Player missing from `attributes.csv` or `positions.csv` (or extra row there) |
| E025 | Required column missing from a file |
| E026 | Row has more cells than the header (nothing is dropped silently) |
| E027 | Duplicate external reference: the same (record_type, source, source_id) is used twice (also catches exact duplicate rows) |
| E028 | Duplicate column name in a header |
| E030 | Unsupported format version |
| E031 | Format version newer than this build supports |
| E032 | No provenance source |
| E033 | File is not valid UTF-8 (tolerant decoding is spec 011) |

### Warnings (load, but listed for review)

| Code | Rule |
|---|---|
| W001 | Club not playable: fewer than 11 players or no goalkeeper (goalkeeper = best position GK, the domain rule) |
| W002 | Outfield player with any goalkeeping attribute > 10 |
| W003 | Goalkeeper with finishing or dribbling > 12 |
| W004 | Age ≥ 34 with pace or acceleration ≥ 17 |
| W005 | All hidden attributes identical (probable unintentional default) |
| W006 | Unknown (well-formed) nation code |
| W007 | Unknown column ignored |
| W010 | Potential ability below derived current ability: raised to CA (`potential_raised` flag) |

W008 (Windows-1252 fallback) and W009 (DD/MM/YYYY dates) are reserved for spec 011.

## State

There are no state transitions in 001. Datasets are immutable values. Loading produces a new
Dataset, and export writes one. Persistence across sessions is spec 004.
