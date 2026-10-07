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
- **Coverage**: 279 clubs, Série A to D, 27 state championships. ✅
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
  site implica o seu acordo com o Termos e Condições". The terms page refuses automated reads
  (HTTP 403), so it **needs a browser check** ⏳.

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
