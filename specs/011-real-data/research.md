# Research: Real Data for Minas Gerais Clubs (spec 011)

## R1. Source survey (US1, FR-001), in progress

This survey covers sources only, not data, so it lives in the public repository. Each source gets
the same fields:
- **coverage**: the Módulo I clubs, and Módulo II where known;
- **freshness**: how recent its newest data is;
- **terms of use and robots**: the exact clause, quoted;
- **fields**: what it provides, mapped to the game's schema.

**Status legend**: ✅ verified on the source (2026-10-07) · ⏳ still to check.

### The 2026 Módulo I clubs (from Wikipedia, ✅)

| Club | City | Stadium | Capacity |
|---|---|---|---|
| América Mineiro | Belo Horizonte | Independência | 23,019 |
| Athletic Club | São João del-Rei | Arena Sicredi | 6,000 |
| Atlético Mineiro | Belo Horizonte | Arena MRV | 46,000 |
| Betim Futebol | Betim | Arena Urbsan | 3,600 |
| Cruzeiro | Belo Horizonte | Mineirão | 61,846 |
| Democrata GV | Governador Valadares | Mamudão | 8,675 |
| Itabirito | Itabirito | Castor Cifuentes | 5,160 |
| North | Montes Claros | Arena Credinor | 5,000 |
| Pouso Alegre | Pouso Alegre | Manduzão | 26,000 |
| Tombense | Tombos | Almeidão | 6,555 |
| Uberlândia | Uberlândia | Parque do Sabiá | 53,350 |
| URT | Patos de Minas | Arena DB | 5,000 |

2026 outcome:
- Cruzeiro champion (1–0 against Atlético in the final);
- Pouso Alegre interior champion;
- Athletic Club and Democrata GV relegated.

These are the reference for SC-003, the synthesis model's strength ranking.

### Sources

**Wikipedia (pt)**
- **Coverage**: all 12 clubs, with competition pages for each season. ✅
- **Terms and robots**: CC BY-SA text licence, and crawling is allowed. ✅
- **Fields**: ✅
  - club name, city, stadium, capacity, founding date, and the competition's results and
    standings;
  - colours are shown as kit images, not text: Cruzeiro's infobox has no colours field. ✅
  - **no current squad**, even for Cruzeiro (perhaps on separate season pages ⏳). Pouso Alegre has
    none either. ✅

**Brasileirinho FC (public pages)**
- **Coverage**: it claims 279 clubs (Série A to D, 27 state championships). ✅ The `/clubes`
  listing shows only Atlético-MG (id 2) and Cruzeiro (id 8) from Minas: perhaps Série A only, or a
  paginated list. Coverage of the other 10 Módulo I clubs is unconfirmed ⏳.
- **Terms and robots**: ✅
  - robots allows `/clubes` and disallows only `/carreira`, `/chat/` and `/admin`;
  - the terms say: "O programa, as telas, os textos e as artes próprias do jogo pertencem ao
    Brasileirinho FC e não podem ser copiados ou republicados sem autorização."
- **Fields**: club page `/clubes/{id}` shows the stadium and capacity, the squad's average age and
  rating, and per player: name, position, age and overall rating. No nationality, attributes,
  shirt number or colours. ✅
- **Note**: the overall ratings are its own work and are **not** an input (owner decision 1).
  Rosters are facts.

**ogol.com.br (zerozero network)**
- **Coverage**: the largest football database (2 M players), with deep lower-league coverage.
  Even Pouso Alegre has a full current squad with a season selector (back to 1913). ✅
- **Fields**: per player: shirt number, position, name (linking to a player page), age,
  nationality, games, market value where known. The club page also gives the stadium and
  capacity, but no colours as text. ✅
- **Terms and robots**: ✅ robots disallows only `/zzmap_v3.php` and lists sitemaps for players and
  teams. The footer says: "© 2003-2026 ZOS, Lda. - Todos os direitos reservados. A utilização deste
  site implica o seu acordo com o Termos e Condições". ✅ **ogol publishes no terms of use.** The
  footer's "Termos e Condições" is plain text, not a link. The help desk (`helpdesk.php?type=1..4`)
  holds contact forms, and type=3 is a GDPR privacy policy only (checked by the owner and by us,
  2026-10-07). What applies is "todos os direitos reservados" and the EU database right (ZOS, Lda.
  is Portuguese), which protects extracting a substantial part. **Owner decision (2026-10-07): use
  it now, gently** (see the spec's Clarifications).

**FootyStats**
- **Coverage**: CSV downloads (league, matches, teams, players) per competition, the state leagues
  included. ✅
- **Terms and robots**: automated fetches of its terms page are refused (HTTP 403). ⏳ The terms
  need reading in a browser.
- **Fields**: player season stats (minutes, goals, cards). ⏳

**ESPN**
- **Coverage**: 2026 player profiles exist for Pouso Alegre's squad (about 29 players, by
  position). ✅
- **Terms and robots**: ⏳
- **Fields**: ⏳ (squad page URL to be found).

**SofaScore**
- **Coverage**: team pages exist for small clubs (Pouso Alegre). ✅
- **Terms and robots**: the terms page has moved (404). ⏳ Its known stance is no automated access.
- **Fields**: ratings and match stats. ⏳

**CBF BID** ([bid.cbf.com.br](https://bid.cbf.com.br/))
- **Coverage**: the official, public daily bulletin of every professional registration, searched by
  date and state (UF). ✅
- **Terms and robots**: ⏳
- **Fields**: contract registrations (athlete, club, contract type, date). No age or position.
  Best used to check who is registered where, not as the squad source.

**FBref (Sports Reference)**
- **Coverage**: ⏳ (probably Série A only).
- **Terms and robots**: automated fetch of its data-use page is refused (HTTP 403). ⏳ It is known to
  cap request rates.

**Transfermarkt**
- **Coverage**: ⏳
- **Terms and robots**: automated fetch refused. ⏳ It is known to forbid automated collection.
- **Fields**: squads, ages, values, contracts. ⏳

**FM-database mods**
- **Terms and robots**: SI's own work, the same reasoning as the ratings. Out.

### Early reading (not a recommendation yet)

- **Clubs**: Wikipedia for identity, stadiums and results (open licence). The owner's review fills
  in colours where text is missing.
- **Squads**: Wikipedia lacks small clubs. ogol is the most complete source (numbers, nationality,
  games, values, even for Pouso Alegre), so its terms are the key open question. Fallbacks:
  Brasileirinho FC rosters (facts only), ESPN, CBF BID.
- **Pages that refuse automated reads** (403): the zerozero, FootyStats and Sports Reference terms.
  They need reading in a browser.
- **Model signals** (minutes, goals, appearances): FootyStats, ogol or ESPN.

## R2. Collecting gently (FR-003)

- **Decision**: a single fetcher for every source.
  - It reads robots.txt (`urllib.robotparser`) and refuses disallowed paths.
  - It sends an honest user agent: `manager-private-import/0.1 (personal, non-public football game;
    github.com/diasmpd/manager)`.
  - It waits at least 4 s between requests to the same host, plus random jitter.
  - It stops a source on HTTP 403 or 429 and reports it, never retrying in a loop.
  - It caches every page gzipped, under `manager-data/cache/<source>/`, with a fetch log (URL, date,
    status).
  - Nothing is fetched again unless `--refresh` asks for it.
- **Why**: the owner's decision to use ogol "gently". A re-import never touches the network.
- **Alternatives**:
  - no cache, which fetches on every build: rejected;
  - parallel fetching, which is impolite: rejected.

## R3. Identity, precedence and provenance (FR-006, FR-008)

- **Decision**:
  - **Player ids**: a player's game id comes from his ogol id (`p-og<id>`), so it is stable across
    re-imports even when names change.
  - **Club ids**: slugs (`cruzeiro`, `pouso-alegre`). Each record's id in each source goes to
    `external_refs.csv`. Each source, with its retrieval date and a licence note, goes to
    `sources.csv` (the 001 format).
  - **Precedence**: owner correction, then ogol (players), then Wikipedia (club identity). Every
    disagreement is listed in the import report.
  - **Name collisions**: same-name players at different clubs are told apart by ogol id. Unresolved
    cases (no id) are flagged, never merged.
- **Why**: the 001 format already models provenance. Stable ids keep owner corrections and saved
  careers valid across seasons.

## R4. The attribute-synthesis model (FR-009 to FR-011)

- **Decision**: two steps, with all parameters in `reference/synthesis/*.toml` (public).

  1. **Overall level (CA, 1–200, FM-like).**

     **Club baseline.** Each club starts from the national division it plays in. The values below
     are a first-fit set and are calibrated:
     - Série A: 125;
     - Série B: 105;
     - Série C: 90;
     - Série D: 80;
     - state league only: 72.

     **Player offsets** around the club baseline:
     - **share of the club's minutes**: regular starter about +12, rarely used about −12;
     - **market value** against the club's median (log scale), when known;
     - **age**: peak 26–30, lower when young or old;
     - **output**: a small bonus for goals and assists per 90 by position.

     **Confidence**:
     - high: minutes and value;
     - medium: one of them;
     - low: neither (only age, position and club).

  2. **Attributes (1–20).**
     - **CA gives a base level**: an attribute mean (about 10.5 at CA 100) that rises with CA.
     - **Position profiles** add per-attribute offsets: a centre-back's heading and marking up, a
       winger's pace, crossing and dribbling up, a goalkeeper's goalkeeping attributes in place of
       outfield ones.
     - **Age curves** shift attribute groups: young players have physical attributes up and mental
       ones down; veterans the reverse.
     - **Variation** is seeded by player id (deterministic), so two players of the same profile
       still differ.
     - **Potential (PA)** comes from CA plus an age-based headroom.
- **Calibration**: SC-003, a Spearman rank correlation of 0.7 or more between the clubs'
  synthesised strength (the game's team strength) and the 2026 Módulo I final table. The model is
  unit-tested on the fictional sample (distribution, profiles and determinism), so tests never need
  private data.
- **Alternatives**:
  - converting other games' ratings: rejected (owner decision);
  - a learned model: no labelled real data to train on.

## R5. Owner corrections and the audit trail (FR-012, FR-013)

- **Decision**: `manager-data/corrections.csv` is append-only, one row per change:
  - columns: `record_type`, `record_id`, `field`, `old_value`, `new_value`, `date`, `note`;
  - the owner edits it in Excel or a text editor, or with `realdata correct …`, which appends a row;
  - the build applies corrections last;
  - each corrected record gets a `manually_edited` flag in `record_flags.csv` (the 001 mechanism).

  On a re-import:
  - a correction whose `old_value` no longer matches the fresh source value is kept, and reported
    as "source changed under a correction";
  - a correction whose record disappeared is kept, and reported.

  The file itself is the field-level history (the open item from 001).
- **Why**: owner values always win. The history shows field, old value, new value and date.

## R6. pt-BR Excel tolerance (format v1.1, FR-015)

- **Decision**: reading tolerates:
  - a byte-order mark;
  - UTF-8 or Windows-1252;
  - `;` or `,` separators (detected from the header);
  - decimal commas;
  - `dd/mm/yyyy` dates;
  - stray spaces.

  Writing stays canonical (format v1). Tested with files re-saved the way pt-BR Excel saves them.

## R7. Keeping real data out of the public repository (SC-006)

- **Decision**: three guards:
  - the CLI refuses to write caches or datasets inside the public repository;
  - a test checks that every dataset tracked in the public repository declares `fictional=true`;
  - the same test checks that no tracked file matches the private repository's layout (`cache/`,
    `corrections.csv`, `datasets/`).
