# Research: Core Domain Model (001)

Phase 0 decisions. Each entry: Decision / Rationale / Alternatives considered.

## R1. Language, packaging and dependencies

- **Decision**: Python ≥ 3.12 (dev machine runs 3.14), packaged with `pyproject.toml` under
  `core/`, src layout (`core/src/manager_core`). **Runtime dependencies: standard library only.**
  Dev-only: `pytest`, `hypothesis` (property tests for round-trip and CA monotonicity), `ruff`,
  `mypy`.
- **Rationale**: the constitution requires each dependency to be justified, and nothing in 001
  needs more than `dataclasses`, `csv`, `datetime` and `argparse`. The `core/` folder leaves room
  for `client/` (Godot, spec 010) at the repo root.
- **Alternatives**: pydantic for validation was rejected, because the importer must collect *all*
  errors with file/row/field locations in pt-BR, which is simpler with a dedicated validator.
  pandas was rejected as heavy and unnecessary for ~330 rows.

## R2. Attribute representation

- **Decision**: one frozen, slotted dataclass `Attributes` with 60 explicit `int` fields (14
  technical, 14 mental, 8 physical, 11 goalkeeping, 13 hidden), plus a registry
  `ATTRIBUTE_GROUPS: dict[AttributeGroup, tuple[str, ...]]` giving FM order and grouping.
  Engines access attributes explicitly: `player.attributes.finishing`.
- **Rationale**: explicit fields are visible to type checkers and IDEs (a prototype lesson: no
  `__getattr__` delegation). One flat object keeps the engine's hot paths cheap. The registry
  drives display, CSV columns and validation from a single source.
- **Alternatives**: nested group dataclasses (`attributes.technical.finishing`) are verbose in
  engine code. A dict of attributes loses typing and is slower.

## R3. Invariants vs. import validation

- **Decision**: two layers.
  1. **Domain constructors** enforce invariants and raise immediately (programming errors).
  2. **Import validator** checks raw CSV rows *before* any domain object is built, collecting
     every error and warning into a `ValidationReport`. Only a report with zero errors proceeds
     to construction (all-or-nothing, FR-019).
- **Rationale**: matches FR-019/020 and the owner's preference for human-review checkpoints.

## R4. CSV dialect for Brazilian Excel (critical for the owner's workflow)

The owner edits in Excel with a pt-BR locale. Out of the box it:
- opens comma-separated files as a single column, and saves with `;` as the separator;
- saves "CSV (separado por vírgulas)" in Windows-1252, or UTF-8 with BOM if "CSV UTF-8" is
  chosen;
- may rewrite ISO dates (`2001-05-14`) as `14/05/2001`;
- may add thousands separators (`15.000.000`) if the cell is formatted that way.

- **Decision (001)**:
  - **Write**: UTF-8 **with BOM**, `;` separator, LF line endings, ISO dates, plain integers,
    rows sorted by id. The output is canonical, so it is byte-stable for determinism and diffs.
    It opens correctly in pt-BR Excel with a double-click.
  - **Read in 001 (canonical only)**: UTF-8 with or without BOM, `;` separator, LF or CRLF,
    trimmed cells, unknown columns raise W007. Anything else is reported as an ordinary error:
    E033 for an undecodable file, or E010 / E004 / E025 on the field.
- **DEFERRED to spec 011** (review decision, 2026-10-02): the tolerant read side below, needed
  only once the owner hand-curates real data.
  - **Read** (tolerant, 011):
    - separator sniffed (`;` or `,`) from the header line;
    - UTF-8 with or without BOM, falling back to Windows-1252 *with a warning* that recommends
      saving as "CSV UTF-8";
    - dates accepted as `YYYY-MM-DD` or `DD/MM/YYYY`;
    - integers accept pt-BR thousands grouping (`^\d{1,3}(\.\d{3})+$`);
    - CRLF and LF both accepted;
    - surrounding whitespace trimmed.
  - `.gitattributes` gains `*.csv text eol=lf` so committed sample files compare byte for byte.
- **Rationale**: SC-008 (fix data in Excel in under 5 minutes) fails if a round-trip through
  Excel breaks the file.
- **Alternatives**: commas with US locale assumed (breaks for the owner). An `.xlsx` workbook
  (rejected by the owner: no git diffs). Tolerant reading in 001 (deferred: no hand curation
  happens before 011).

## R5. File layout of a dataset

- **Decision**: a dataset is a folder of tables. Wide tables are used where the owner edits by
  hand, matching how FM editors show players. Full column specs are in
  [contracts/csv-format.md](contracts/csv-format.md).

  | File | Rows | Purpose |
  |---|---|---|
  | `dataset.csv` | 1 | format version, reference date, fictional flag, tool + version, seed, notes |
  | `sources.csv` | 1..n | provenance sources (name, url, retrieved_on, licence/notes) |
  | `clubs.csv` | clubs | club identity, stadium, reputation |
  | `players.csv` | players | identity, physical profile, feet, potential ability |
  | `attributes.csv` | players | `player_id` + 60 attribute columns |
  | `positions.csv` | players | `player_id` + 14 position columns (blank = 1) |
  | `squads.csv` | memberships | player → club, shirt number, value/wage/contract (+ currency) |
  | `external_refs.csv` | 0..n | (record_type, record_id, source, source_id) |
  | `record_flags.csv` | 0..n | per-record provenance flags (hidden_defaulted, potential_defaulted, potential_raised). Flags persist across exports. |

  (`integrity.csv` for manual-edit detection is deferred to 011, as format v1.1.)

- **Rationale**: one concern per file keeps each table narrow enough to edit (attributes are the
  only very wide one, by design). Free agents are simply players with no `squads.csv` row.
- **Alternatives**: one giant players table with ~95 columns is error-prone in Excel. JSON was
  rejected by the owner.

## R6. Detecting manual edits: DEFERRED to spec 011

Moved to 011 by the review decision (2026-10-02), together with the tolerant Excel read side.
Kept here as 011's starting design. Open points for 011:
- A per-record hash shows *that* a record was edited, not *which field*. 011 must decide whether
  to store previous canonical values so the field-level diff is auditable.
- `record_flags.csv` flags persist across exports. Only `integrity.csv` is rewritten.

- **Original design**: on export, write `integrity.csv` with a SHA-256 of each record's canonical
  serialisation, covering the record's rows across all files. On import, a record whose hash
  differs gets a `manually_edited` flag, and a record missing from `integrity.csv` gets
  `added_manually`. If `integrity.csv` is absent (hand-built datasets), no edit flags are
  produced. The next export rewrites `integrity.csv`.
- **Rationale**: auditability without asking the owner to log edits, consistent with Carta
  Convite's audit-trail approach. The hash covers canonical values, not bytes, so Excel's
  re-formatting alone (dates, BOM, separators) does not count as an edit.
- **Alternatives**: timestamps in rows (Excel noise, not reliable); git history only (doesn't
  travel with exported datasets).

## R7. Position suitability (FR-012) and familiarity

- **Decision**:
  - `suitability(player, pos) = base(pos) × familiarity_factor(fam)`, where `base` is a weighted
    mean of the position's key attributes (1–20 scale). The weights live in a data file
    `reference/position_weights.csv`, derived from FM's key attributes per position (as
    highlighted in FM's player-profile screen).
  - `familiarity_factor` interpolates linearly between FM band anchors:

    | Familiarity | 20 | 18 | 15 | 12 | 9 | 5 | 1 |
    |---|---|---|---|---|---|---|---|
    | Factor | 1.00 | 0.99 | 0.96 | 0.90 | 0.82 | 0.70 | 0.55 |

- **Rationale**: in FM, Natural and Accomplished players are close, and penalties grow steeply
  below Competent. The prototype's linear factor penalised Accomplished players by 11%, which is
  too harsh. Weights as data allow tuning in later specs without code changes.
- **Alternatives**: FM's exact internal role-ability formula is not public, and roles and duties
  only arrive in 006.

## R8. Current Ability derivation (FR-009)

- **Decision**: `CA = round(1 + (S − 1) × 199 / 19)`, clamped to 1–200, where
  `S = 0.85 × max_pos base(pos) + 0.15 × mean(all visible attributes relevant to the player's
  type)` (outfield: technical + mental + physical; GK: goalkeeping + mental + physical).
  `max_pos` ranges over positions where familiarity ≥ 15.
- **Properties**:
  - **Monotonic**: all weights are positive, max and mean are non-decreasing, and the clamp is
    monotonic. A property test (hypothesis) checks this.
  - **Rough mapping (not a calibration target)**: key attributes around 15 → CA ≈ 150 (top
    Brazilian Série A); around 9 → CA ≈ 85 (Série D / small Mineiro club). It will be
    re-calibrated in 011 against named, dated sources (Constitution I v1.1).
- **Rationale**: CA is derived, never stored, so it cannot contradict the attributes (owner's
  choice Q1). Including a small share of general attributes mirrors FM, where every attribute
  costs CA.
- **PA handling**:
  - `PA` absent → `PA = CA` with the `potential_defaulted` flag.
  - `PA < CA` → PA is raised to CA, with the `potential_raised` flag and warning **W010**.
  - This is never a blocking error: the CA formula is a rough mapping that will be re-calibrated
    (011), and a re-tune that raises CA must not make old datasets fail to import.

## R9. Best-XI assignment (FR-013, SC-006)

- **Decision**: exact **bitmask dynamic programming** over the 11 formation slots:
  `dp[mask]` holds the best total with the slots in `mask` filled, iterating over players in id
  order. Cost is about 25 × 2,048 × 11 ≈ 560k steps. A reviewer benchmark measured 0.09 s for 27
  players on Python 3.14 on the reference PC.
  - **Integer scores**: the assignment uses `round(suitability × 1000)` (integer milli-points),
    never float sums. Float totals that are mathematically equal can differ in the last bit
    depending on summation order, which would make tie-breaks machine-dependent
    (Constitution II).
  - **Ties**: broken exactly: higher integer total, then the lexicographically smaller tuple of
    player ids in slot order. A dedicated test builds lineups with deliberately equal totals. A GK-slot filled by a non-goalkeeper raises a flag (User Story 3, scenario 3).
- **Rationale**: exact optimum (SC-006), standard library only, deterministic.
- **Alternatives**: scipy `linear_sum_assignment` (Hungarian) is exact but brings a heavy
  dependency into a stdlib-only core, and its tie-breaking is not under our control. A greedy
  pick is not optimal (prototype lesson).

## R10. Formations catalogue (FR-014)

- **Decision**: `reference/formations.csv` with one row per (formation, slot_index,
  position_code, x_m, y_m). The 5 standard formations come from the prototype, whose slot
  coordinates in metres on 105 × 68 were worth keeping. Formations are loaded as data, which
  lets custom formations, attacking and defending shapes, and free placement (owner's direction)
  extend the same structure later.
- **Rationale**: coordinates cost nothing now and are what 006/007 will need. A slot keeps a
  position code for familiarity and suitability.

## R11. Identifiers and reference lists

- **Decision**:
  - IDs are lowercase slugs `^[a-z0-9][a-z0-9-]{1,47}$`: clubs like `vale-do-ouro`, players
    like `p-000123` in the sample (real data may use any slug).
  - Nationality: 3-letter **FIFA trigram** (e.g. BRA, ARG, ENG). These are validated against a
    bundled `reference/nations.csv` covering CONMEBOL, UEFA's main nations, CONCACAF majors and
    other common origins. An unknown but well-formed code is a **warning**, so the list can grow
    without blocking imports.
  - Brazilian state (UF): the 27 codes, validated when `country = BRA`.
  - Currency: ISO 4217 code (BRL, EUR, USD).
- **Rationale**: football data uses FIFA codes (England/Scotland are separate nations in FM;
  ISO alpha-3 has no ENG). Warnings keep the list open-ended.

## R12. Localisation (Constitution: no hard-coded user-facing strings)

- **Decision**: a minimal `i18n` module with `t(key, **params)` and a `pt_BR` message catalogue.
  The CLI output and validation messages go through it. Code identifiers and keys stay English.
- **Rationale**: it satisfies the constitution at low cost, and validation messages read
  naturally for the owner. Adding `en` later is just one more catalogue.

## R13. Facade and CLI (Constitution III)

- **Decision**: `manager_core.api` is the thin facade (see [contracts/facade.md](contracts/facade.md)).
  The CLI (`python -m manager_core …`, argparse) calls only the facade. Commands are listed in
  [contracts/cli.md](contracts/cli.md).
- **Rationale**: the M0 terminal UI (005) and the later Godot API (010) build on the same facade.
  No game rules live in UI code.
- **Note**: in 001, callers hold and pass a `Dataset` object, which is fine in-process for M0.
  Spec 004 (saves) and spec 010 (out-of-process API) will replace it with a session/handle.

## R14. Sample world generator (FR-024..028)

- **Decision**:
  - Deterministic generator `manager_core.sample` with its own `random.Random(seed)`. Default
    seed `20261002`. Output goes to `data/sample/` (committed).
  - **Clubs**: 12 fictional clubs from curated names (fictional towns styled after Minas Gerais,
    no real club names).
  - **Tier quality**: mean key-attribute level of about 13.5 for strong, 10 for mid and 8 for
    small clubs, with per-player spread.
  - **Squads**: 27 players per club, including 3 GK and at least 2 natural players per line.
  - **Players**:
    - Position-archetype attribute templates.
    - Height and weight by position.
    - Feet: about 75% right, 20% left, 5% two-footed.
    - Hidden attributes: N(10, 3.5), clamped.
    - PA = CA + age-dependent headroom (younger players get more).
- **Test**: a byte-for-byte comparison of the generator output against the committed files
  (SC-002). The generator version is written to `dataset.csv`, so any intentional change shows up
  as a version bump plus a regenerated diff.

## R15. CI (Constitution: Development Workflow)

- **Decision**: GitHub Actions workflow `.github/workflows/ci.yml` runs `ruff`, `mypy` and
  `pytest` on Windows and Ubuntu, Python 3.12 and 3.14. There is no calibration gate yet, because
  001 has no simulation. 001 is the first code spec, so CI starts here.
