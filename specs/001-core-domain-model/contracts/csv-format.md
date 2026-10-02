# Contract: Dataset CSV Format v1.0

This is a public contract. `manager-data` and spec 011 produce datasets in this format, and the
core imports and exports them. Changing it requires a `format_version` bump (minor = additive and
backward-compatible, major = breaking).

## General rules

- **Folder**: one folder per dataset, with file names as below (lowercase).
- **Encoding**: written as UTF-8 with BOM. Read: UTF-8 (BOM optional), with a Windows-1252
  fallback that raises W008.
- **Separator**: written as `;`. Read: `;` or `,`, sniffed from the header.
- **Lines**: written with LF. Read: LF or CRLF.
- **Header row**: required. Column order doesn't matter on read, and unknown columns raise W007.
  Written in the order listed below.
- **Empty cell** = absent value.
- **Dates**: written as `YYYY-MM-DD`. Read: also `DD/MM/YYYY` (W009).
- **Integers**: plain digits. Read: also pt-BR grouping such as `15.000.000`.
- **Booleans**: `true` / `false` (read case-insensitive, and also `sim` / `não`).
- **List cells** (nationalities): `|`-separated, e.g. `BRA|ITA`.
- **Row order on write**: sorted by primary key, so output is byte-stable.

## Files

### dataset.csv (exactly 1 data row)
`format_version; reference_date; fictional; tool; tool_version; seed; notes`

### sources.csv (≥ 1 row)
`name; url; retrieved_on; licence_notes`

### clubs.csv
`club_id; name; short_name; abbreviation; city; state; country; color_primary; color_secondary; stadium_name; stadium_capacity; founded_year; reputation`

### players.csv
`player_id; full_name; display_name; date_of_birth; nationalities; height_cm; weight_kg; left_foot; right_foot; potential_ability`

`potential_ability` may be empty. It then defaults to the derived CA, with the
`potential_defaulted` flag.

### attributes.csv
`player_id` followed by the 60 attribute columns in FM order, using the snake_case names from
[data-model.md](../data-model.md#attributes-60-integers-each-120-e004). The 47 visible columns
are required. Hidden columns may be absent or empty: documented defaults apply, with the
`hidden_defaulted` flag.

### positions.csv
`player_id; GK; DL; DC; DR; WBL; WBR; DM; ML; MC; MR; AML; AMC; AMR; ST`. An empty cell means
1 (Ineffectual).

### squads.csv
`player_id; club_id; shirt_number; market_value; wage_monthly; currency; contract_expiry`.
Players without a row are free agents.

### external_refs.csv (optional)
`record_type; record_id; source; source_id` (record_type ∈ `club`, `player`)

### record_flags.csv (optional; written by the core)
`record_type; record_id; flag; detail`

### integrity.csv (optional; written on export)
`record_type; record_id; sha256`. The hash is over the record's canonical values (not bytes),
so Excel re-formatting alone doesn't count as an edit. Records whose hash changed get
`manually_edited`, and unknown records get `added_manually` (research R6).

## Reference data bundled with the core (not part of a dataset)

These live in `core/src/manager_core/reference/` as CSV in the same dialect.

- **formations.csv**: `formation; slot; position; x_m; y_m` for 4-4-2, 4-3-3, 4-2-3-1, 3-5-2
  and 5-3-2.
- **nations.csv**: `code; name_pt; confederation`.
- **position_weights.csv**: `position; attribute; weight`. Initial weights below, after FM's
  key attributes per position. Mirrored positions (DR/DL, WBR/WBL, MR/ML, AMR/AML) share
  weights.

| Position | Key attributes (weight) |
|---|---|
| GK | reflexes 3, handling 2, one_on_ones 2, aerial_reach 1.5, command_of_area 1.5, positioning 1.5, communication 1, concentration 1, kicking 0.5, rushing_out 0.5, agility 1 |
| DC | tackling 2, marking 2, positioning 2, heading 1.5, jumping_reach 1.5, strength 1, anticipation 1, concentration 1, bravery 1, pace 0.5, decisions 0.5, composure 0.5 |
| DL/DR | tackling 1.5, marking 1.5, positioning 1.5, pace 1.5, acceleration 1, stamina 1, work_rate 1, crossing 1, anticipation 1, concentration 0.5, passing 0.5, teamwork 0.5 |
| WBL/WBR | crossing 1.5, pace 1.5, stamina 1.5, work_rate 1.5, acceleration 1, dribbling 1, tackling 1, off_the_ball 1, teamwork 1, passing 0.5, technique 0.5, marking 0.5 |
| DM | tackling 1.5, positioning 1.5, anticipation 1.5, passing 1.5, decisions 1, teamwork 1, work_rate 1, marking 1, concentration 1, composure 0.5, strength 0.5, stamina 0.5 |
| MC | passing 2, decisions 1.5, vision 1.5, first_touch 1, technique 1, teamwork 1, work_rate 1, stamina 1, composure 1, anticipation 0.5, off_the_ball 0.5, tackling 0.5 |
| ML/MR | crossing 1.5, dribbling 1.5, pace 1.5, acceleration 1, passing 1, technique 1, work_rate 1, stamina 1, off_the_ball 1, teamwork 0.5, first_touch 0.5 |
| AMC | passing 1.5, vision 1.5, technique 1.5, first_touch 1, dribbling 1, flair 1, decisions 1, off_the_ball 1, composure 1, long_shots 0.5, finishing 0.5, agility 0.5 |
| AML/AMR | dribbling 2, pace 1.5, acceleration 1.5, technique 1, crossing 1, flair 1, off_the_ball 1, first_touch 1, agility 1, finishing 0.5, balance 0.5 |
| ST | finishing 2.5, off_the_ball 1.5, composure 1.5, first_touch 1, anticipation 1, pace 1, acceleration 1, heading 1, strength 0.5, dribbling 0.5, technique 0.5, balance 0.5 |
