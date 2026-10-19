# 011 Real data: South American top-two divisions, source survey

Scope: top two men's football divisions of Argentina, Bolivia, Chile, Colombia, Ecuador, Paraguay, Peru, Uruguay and Venezuela. Brazil skipped (covered elsewhere).

Research date: 2026-10-07.

## Method and rules followed

- No bulk download. Each host was asked for `robots.txt` only (one request per host, background script with `sleep 5` between hosts). Ad-hoc page fetches were one request per host per call; they were not timed by a separate timer, so the 5-second spacing is guaranteed only for the robots run.
- User agent for robots requests: `ManagerResearchBot/0.1 (personal non-commercial research; contact: bgmateushenrique@gmail.com)`. The WebFetch tool uses its own user agent.
- Where a site returned a bot challenge, a 403, or refused the fetcher, that is recorded as a refusal. No attempt was made to get around it.
- Cell marks: **Verified** = read in this session (robots.txt body or a fetched terms/page), with quotes as returned by the fetcher. **Unverified** = from a search snippet, a third-party page, memory, or not checked.

Quotes from WebFetch are the fetcher's extraction. Confirm exact wording in a browser before relying on it for a legal decision.

## Summary table

| Source | Coverage (divisions / clubs) | Freshness of newest data | Terms of use and robots.txt | Fields provided |
|---|---|---|---|---|
| **ogol.com.br** (zerozero network) | Unverified. Country pages not reached. | Unverified | **Verified: refused.** robots.txt returned HTTP 403 with a Cloudflare "Just a moment..." challenge page, so no robots rules could be read. Terms not checked (no fetch allowed). | Unverified |
| **zerozero.pt** | Unverified (not requested directly, same network) | Unverified | Unverified. Not fetched. | Unverified |
| **Wikipedia** (en / es, per-country league and club articles) | **Verified:** Argentina Liga Profesional page lists 30 clubs for 2026 (two zones of 15). Club squad sections not confirmed. Other countries unverified. | **Verified:** en page shows "Current: 2026" and the 2026 Apertura champion. | **Verified:** en.wikipedia robots.txt returns 200 and disallows only specific paths (e.g. `/wiki/Special:`); `User-agent: *` has no blanket ban. **Verified:** reuse page says content is CC BY-SA and GFDL, with attribution and share-alike; it "does not address the reuse of data or facts." Media files have their own licences. | Club pages: name, colours (infobox, likely; unverified), squad lists on some club pages (unverified). Season tables, champions, top scorers. |
| **FootyStats** (country CSV downloads) | Unverified. Country dataset pages exist for many leagues (e.g. Faroe, Myanmar, NZ). No South American page was opened. | Unverified | **Verified (robots):** `User-agent: *` has `Disallow: /c-dl.php` and `Disallow: /c-dl.php*` (the CSV download script), plus `Disallow: /api/club*`, `/api/team*`, `/api/match*`, `/api/register*`. ClaudeBot has `Crawl-delay: 1` (named rule). **Refused:** `footystats.org/terms-of-use` returned HTTP 403 to the fetcher; terms not read. Dataset page says for scripted access "please use our API". | CSV for league, matches, teams, players (from search snippet of a dataset page; unverified field list). |
| **ESPN** (ESPN Deportes squad pages `espndeportes.espn.com/futbol/equipo/plantel/...`) | **Verified by search result only:** squad pages exist for clubs in Bolivia (Always Ready, Blooming, Aurora, The Strongest, Oriente Petrolero, Real Tomayapo, others), Chile (Colo Colo, Universidad de Chile, Ñublense), Uruguay (Central Español). Full league lists unverified. | Mixed. Pages found were dated 2014 for Chile, 2026-era for Bolivia (league position shown, season unclear). Unverified. | **Verified (robots):** `www.espn.com/robots.txt` returns 200. `User-agent: *` lists many `Disallow` paths; none found for `plantel` or `equipo`. Named bots (GPTBot, anthropic-ai, Google-Extended, CCBot, ChatGPT-User, claritybot, Bytespider, FacebookBot, etc.) have `Disallow: /`. **Verified (terms, Disney ToU, last updated 2024-05-24, which list ESPN as covered):** "access, monitor, copy or extract the Disney Products using a robot, spider, script, or other automated means"; "data mining or web scraping or otherwise compiling, building, creating or contributing to any collection of data"; "for your personal, noncommercial use only"; "we do not allow uses of the Disney Products ... that are commercial". | Squad pages: player name, position, age, height, weight, nationality (Bolivia search snippet). League position. |
| **SofaScore** | Unverified. Coverage not checked. | Unverified | **Verified (robots):** `www.sofascore.com/robots.txt` returned HTTP 403 (JSON error body). **Verified:** `/terms-of-use` returned HTTP 404. Search snippet (not verified against site) says SofaScore states that "due to agreements with our data providers, we are unable to share the data sources in the form of API endpoints". No public API. | Unverified |
| **FBref / Sports Reference** | Unverified. Coverage not checked. | **Search result (news, unverified against primary source):** Sports Reference says its advanced-stats provider (Opta) terminated access and required deletion of advanced data (2026). Sources: linkiesta.it (2026-01), awfulannouncing.com, valoraanalitik.com. | **Verified (robots):** `fbref.com/robots.txt` returned a Cloudflare "Just a moment..." challenge page (refused to automated reads). Terms not read. Search snippets only: a mirror of Stats Perform terms says material is "solely provided to you for personal, non-commercial use" (mirror, unverified). | Unverified (advanced stats reportedly removed) |
| **Transfermarkt** | Unverified. Coverage not checked (site refused fetch). | Unverified | **Verified (robots):** `User-agent: wget` → `Disallow: /`; `User-agent: *` → `Allow: /`. **Refused:** WebFetch returned "Claude Code is unable to fetch from www.transfermarkt.com", so the terms page was **not read**. **Unverified (secondary sources only):** a third-party article says the terms bar "bots, spiders, screen scraping, and other automated processes"; a 2018 mailing-list post quotes a legal notice that partial reproduction needs prior written consent. Treat as a lead. | Market values and squad lists are the usual Transfermarkt fields. Unverified for this survey. Win Sports cites it for market values in Colombia (secondary). |
| **AFA Argentina** (`afa.org.ar`) | Unverified. Argentina top two divisions per Wikipedia (see above). | Unverified | **Verified:** robots request returned 301 (Cloudflare), not followed. Terms not read. | Unverified |
| **FBF Bolivia** (`fbf.bo`) | Unverified. | Unverified | **Verified:** robots request returned no connection (HTTP 000). Terms not read. | Unverified |
| **ANFP Chile** (`anfp.cl`) | Search snippet (not verified against site): 32 clubs associated across Primera División and Primera B. Clubs with 2015 website list in an ANFP PDF. | Unverified (search snippet shows ANFP publishes squad lists per club for 2022 Campeonato). | **Verified (robots):** `User-agent: *` disallows only `/wp-admin/`. **Verified:** the file also has a block with the header "Crawlers de IA con comportamiento abusivo (2026-08-22)" that sets `Disallow: /` for `ClaudeBot`, `anthropic-ai`, `GPTBot`, `CCBot`, `PerplexityBot`, `Bytespider`, and others. **This site excludes AI crawlers including Anthropic's. No page of anfp.cl was fetched beyond robots.txt.** Terms not read. | Unverified |
| **Dimayor Colombia** (`dimayor.com.co`) | Liga BetPlay top two (search snippets: Liga BetPlay clubs; 2026 Apertura roster moves reported by ESPN Colombia, Win Sports). Official team squad pages not found in search. | ESPN Colombia 2026 roster-moves note (search snippet; date not checked). | **Verified (robots):** `User-agent: *` → `Disallow: /wp-admin/`, `Allow: /wp-admin/admin-ajax.php`; sitemap at `/sitemap.xml`. Terms not read. | Unverified |
| **FEF Ecuador / LigaPro** (`fef.ec`, `ligapro.ec`) | LigaPro Serie A 2026 (search snippet, Primicias): 30-date first stage starting 2026-02-20. Team squad pages found on Primicias (not on the official sites). | **Search snippet:** Primicias article dated Sept 2026 (104 foreign players in LigaPro 2026). Newest found. | **Verified (robots):** `fef.ec/robots.txt` returned 301 (nginx), not followed. `ligapro.ec` not checked. Terms not read. | Primicias squad pages: position, nationality, age, sometimes height and weight. Official fields unverified. |
| **APF Paraguay** (`apf.org.py`) | Unverified. Primera División clubs not confirmed by an official source. Wikipedia pages exist for 2018–2024 APF Divisional seasons. | Search result: Última Hora article dated July 2026 on Cerro Porteño pre-Apertura. | **Verified (robots):** `User-agent: *` → `Disallow: /api/`, `/preview/`, `/_next/`. Googlebot/Bingbot/YahooSlurp → `Allow: /`. Sitemap at `/sitemap.xml`. Terms not read. | Unverified |
| **FPF Peru / Liga 1** (`fpf.org.pe`) | **Search snippet:** Liga 1 2026, 18 clubs (ADT, Alianza Atlético, Alianza Lima, Atlético Grau, Cienciano, Comerciantes Unidos, Cusco FC, Deportivo Garcilaso, Deportivo Moquegua, FBC Melgar, FC Cajamarca, Juan Pablo II, Los Chankas, Sport Boys, Sport Huancayo, Sporting Cristal, Universitario, UTC). Second division not checked. | 2026 Apertura, Clausura started 19 July (search snippet, mid-season). | **Verified:** robots request for `fpf.org.pe` returned no connection (HTTP 000). Terms not read. | Unverified (no squads found) |
| **AUF Uruguay** (`auf.org.uy`) | **Search snippet:** 2026 Liga AUF Uruguaya, 16 clubs (Albion, Cerro, Boston River, Racing, Progreso, Peñarol, Juventud, Wanderers, Defensor Sporting, Cerro Largo, Montevideo City Torque, Central Español, Deportivo Maldonado, Nacional, Danubio, Liverpool). Squad pages found on third-party sites only. | Search snippet: standings after three rounds (RSSSF). Newest data found is early season 2026. | **Verified (robots):** `User-agent: *` has no Disallow rules; only a sitemap line. Terms not read. | Official squad pages not found. Third-party: FotMob (Nacional), 365Scores (Progreso), ESPN Deportes (Central Español). |
| **FVF Venezuela / Liga FUTVE** (`fvf.com.ve`, `laligafutve.com`) | Unverified. Liga FUTVE is the top flight (Wikipedia). | **Search result:** newest season found is 2024 (Deportivo Táchira champion). 2025/2026 not found. | **Verified (robots):** `fvf.com.ve/robots.txt` has only a sitemap line, no Disallow. Terms not read. | Unverified |

## Per-source notes

### ogol.com.br (zerozero network)
- robots.txt is behind a Cloudflare bot challenge (HTTP 403 with "Just a moment..." HTML). Treat as refused. Do not try to get past it.
- Web search found no terms text for Ogol or ZeroZero. The footer link "Termos de Uso" on ogol.com.br and zerozero.pt needs a manual read.

### Wikipedia (en, es)
- Best free source for league membership, season status, champions and club names. Squads are inconsistent across club pages.
- Reuse: CC BY-SA 4.0 with attribution and share-alike (verified via reuse page). Wikipedia does not claim rights over facts, but its licensing page does not address data reuse. Using it for the game's content (names, facts) needs attribution in the credits.
- Good first candidate for club identity and league membership. Not sufficient for squads.

### FootyStats
- robots.txt blocks `/c-dl.php` (CSV download) and `/api/club*`, `/api/team*`, `/api/match*` for all unnamed bots. The site points to its own paid API for scripted use. That combination means scripted CSV pulls go against the robots rules, and the API is the intended channel.
- Terms page refused the fetcher (HTTP 403). Terms unknown. Check the API documentation and its pricing before any use.
- Country-level CSVs for South American leagues were not confirmed in this survey.

### ESPN Deportes (squad pages)
- Best squad coverage found in this survey: `espndeportes.espn.com/futbol/equipo/plantel/_/id/<id>` pages for Bolivian, Chilean and Uruguayan clubs, with player name, position, age, height, weight, nationality.
- robots.txt does not block the `plantel` path for `*`.
- **Terms forbid automated use.** The Disney terms that cover ESPN prohibit "robot, spider, script, or other automated means" and "web scraping". Scraping these pages would breach the terms, even though robots.txt allows the path. Use only for manual reference unless the owner licenses the data.
- Some pages are stale (2014 Chile URLs seen in search).

### SofaScore
- robots.txt returned 403 to curl. The terms URL tried (`/terms-of-use`) returned 404. The correct terms URL was not found.
- Search snippet (secondary): no public API because of data-provider agreements. Assume automated access is not permitted until the terms are read.

### FBref / Sports Reference
- robots.txt is behind a Cloudflare challenge. Treat as refused.
- Freshness risk: reports (2026) say the advanced-stats provider terminated access and advanced data was removed from FBref. Basic match and table data may still exist. Verify on the site before relying on it.

### Transfermarkt
- robots.txt is permissive for `*` (`Allow: /`) and blocks `wget` entirely. The fetcher refused the site, so the terms could not be read in this session.
- Secondary sources say the terms prohibit bots and scraping and bar reproduction without written consent. Treat as forbidden for automated use until a written licence is obtained or the terms are read directly.
- Market values and squads (the best fields for this project) are on this site, which makes it the most important source to clear with the owner before any build.

### Federation sites
- **ANFP (Chile)**: robots.txt names Anthropic's crawlers (`ClaudeBot`, `anthropic-ai`) with `Disallow: /`. Do not use this site for automated reads from this project. The rest of the robots rules are not an issue.
- **AFA (Argentina), FBF (Bolivia), FPF (Peru), FEF (Ecuador)**: robots.txt not readable (redirect, challenge or no connection). Retry later manually.
- **Dimayor (Colombia), APF (Paraguay), AUF (Uruguay), FVF (Venezuela)**: robots.txt readable and does not block general pages (`/wp-admin/` for Dimayor, `/api/`, `/preview/`, `/_next/` for APF). Terms not read; check them before any automated use.
- No federation site was found to publish a full squad list with player fields in this survey. Federations publish registration lists in PDFs (ANFP 2022 example in search results). Unverified for each.

## Answers to the three questions

1. **Most clubs with squads**: ESPN Deportes squad pages (Bolivia, Chile, Uruguay, and probably others, unverified for Colombia, Ecuador, Peru, Paraguay, Venezuela). Coverage per country not counted. Terms forbid automated use, so this is a reference, not a feed.
2. **Terms that forbid automated use**:
   - ESPN: Disney terms prohibit robots, scraping and data mining (verified).
   - Transfermarkt: secondary sources only (fetch refused). Treat as forbidden until read.
   - SofaScore: secondary sources say no public API and data-provider agreements (not read directly).
   - FootyStats: robots blocks the CSV download script for unnamed bots; API is the stated channel (verified from robots).
   - ANFP Chile: robots blocks AI crawlers including Anthropic's (verified).
   - FBref and ogol.com.br: bot challenges (refused).
3. **Unverified**:
   - All South American club lists beyond those in search snippets (Argentina 30 clubs verified via Wikipedia; others are search snippets).
   - Colours, age, nationality, position and market value field coverage for each source (only ESPN and Primicias squad fields seen in search snippets).
   - Terms text for: Transfermarkt, FootyStats, SofaScore, FBref, Ogol/ZeroZero, FotMob, 365Scores, all federation sites, and LigaPro.
   - Freshness for Venezuela (only 2024 found), Chile (ANFP current data), Bolivia (2026 status), Paraguay (only one club article).
   - Whether any of these sites offers a licensed data feed or API for South America.

## Suggested next steps for the owner

- Read the terms of Transfermarkt, FootyStats (API terms), SofaScore and FBref directly in a browser, and record the exact wording here.
- Ask whether a licensed API (FootyStats API, or a sports-data licence) is acceptable for the project. The FootyStats robots file points to one.
- Decide whether manual reference (no bots) is enough for the first milestone. Unverified claims above need a human read before any build.

Nothing was downloaded in bulk. Nothing was committed or pushed.
