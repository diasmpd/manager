"""ogol.com.br page parsers (spec 011 R1/R3): a club page (identity, colours, squad) and a player
page (personal facts, career by season). Owner decision 2026-10-07: ogol is used gently, for
private use only; pages come from the polite fetcher's cache.
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass, field

BASE = "https://www.ogol.com.br"
SEASON_2026 = 155  # ogol's epoca_id for 2026
# squad sections; "Jogador" lists players with no position on the club page ("?": the player
# page says)
GROUPS = {"Goleiro": "GK", "Defensor": "D", "Meia": "M", "Meio-campista": "M", "Atacante": "A",
          "Jogador": "?"}
FEET = {"Destro": "right", "Canhoto": "left", "Ambidestro": "both"}


@dataclass(frozen=True, slots=True)
class SquadEntry:
    ogol_id: int
    slug: str  # the player page is /jogador/<slug>/<ogol_id>
    name: str
    group: str  # GK, D, M, A or ? (unknown)
    number: int | None
    nationality: str
    age: int | None
    market_value_eur: int | None
    active: bool  # False: listed for the season but no longer at the club


@dataclass(frozen=True, slots=True)
class RawClub:
    name: str
    founded: str | None
    city: str | None
    state: str | None
    colors: tuple[str, str] | None
    squad: tuple[SquadEntry, ...]
    stadium: str | None = None
    capacity: int | None = None


@dataclass(frozen=True, slots=True)
class SeasonLine:
    season: str
    team_id: int | None
    games: int
    goals: int
    assists: int
    team_path: str = ""  # e.g. /equipe/america-mineiro (own-club links carry no id)


@dataclass(frozen=True, slots=True)
class RawPlayer:
    ogol_id: int
    full_name: str | None
    birth_date: str | None
    nationality: str | None
    position: str | None
    foot: str | None
    height_cm: int | None
    weight_kg: int | None
    career: tuple[SeasonLine, ...] = field(default=())


_ROW_END = re.compile(r'<div class="card-data(?:__row|__header|__body|__footer|[ "])|<h2|<table'
                      r'|<div id="|<script')


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _cards(page: str) -> dict[str, str]:
    """Label -> text of every `card-data__row` (the first one wins)."""
    out: dict[str, str] = {}
    rows = re.split(r'<div class="card-data__row[^"]*"', page)[1:]
    for row in rows:
        label = re.search(r'<span class="card-data__label">(.*?)</span>', row, re.S)
        if not label:
            continue
        rest = row[label.end():]
        key = _text(label.group(1))
        if key not in out:  # the last row ends where its card does, not at the page's end
            out[key] = _text(_ROW_END.split(rest, maxsplit=1)[0])
    return out


def _colour(value: str) -> str:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return "#" + value.upper()


def _money(text: str) -> int | None:
    """'150 mil €' -> 150000; '1,5 M €' -> 1500000."""
    match = re.search(r"([\d.,]+)\s*(mil|M)\s*€", text)
    if not match:
        return None
    number = float(match.group(1).replace(".", "").replace(",", "."))
    return round(number * (1_000 if match.group(2) == "mil" else 1_000_000))


def parse_club(page: str) -> RawClub:
    main = re.search(r"--entity-color-main\s*:\s*(#[0-9a-fA-F]{3,6})", page)
    complement = re.search(r"--entity-color-complementary\s*:\s*(#[0-9a-fA-F]{3,6})", page)
    colors = (_colour(main.group(1)), _colour(complement.group(1))) if main and complement else None
    squad: list[SquadEntry] = []
    block = page.split('id="team_squad"', 1)[1] if 'id="team_squad"' in page else ""
    block = block.split('<div class="section">Treinador', 1)[0]
    for section in re.split(r'<div class="section">', block)[1:]:
        title = section.split("</div>", 1)[0].strip()
        group = GROUPS.get(title)
        if group is None:
            continue
        for match in re.finditer(r'<div class="staff( inactive)?">(.*?)(?=<div class="staff|$)',
                                 section, re.S):
            row = match.group(2)
            link = re.search(r'href="/jogador/([a-z0-9-]+)/(\d+)[^"]*">(.*?)</a>', row, re.S)
            if not link:
                continue
            number = re.search(r'<div class="number">(.*?)</div>', row)
            nation = re.search(r'<a title="([^"]+)" href="/pais/', row)
            age = re.search(r"(\d+) anos", row)
            squad.append(SquadEntry(
                ogol_id=int(link.group(2)), slug=link.group(1), name=_text(link.group(3)),
                group=group,
                number=int(number.group(1)) if number and number.group(1).isdigit() else None,
                nationality=nation.group(1) if nation else "",
                age=int(age.group(1)) if age else None,
                market_value_eur=_money(htmllib.unescape(row)),
                active=match.group(1) is None))
    cards = _cards(page)
    city, state = cards.get("Cidade"), None
    if city:  # "Pouso Alegre (MG)" or "Betim, MG"
        found = re.match(r"(.*?)\s*(?:\((\w{2})\)|,\s*(\w{2}))$", city)
        if found:
            city, state = found.group(1), found.group(2) or found.group(3)
    founded = cards.get("Ano de Fundação")
    if founded and re.fullmatch(r"\d{4}-00-00", founded):  # only the year is known
        founded = founded[:4]
    stadium = re.search(r'<div id="stadium">.*?<div class="name"><span><a[^>]*>(.*?)</a>', page,
                        re.S)
    capacity = re.search(r"Lotação\s*<span>\s*([\d.]+)", page)
    return RawClub(cards.get("Nome", ""), founded, city, state, colors, tuple(squad),
                   _text(stadium.group(1)) if stadium else None,
                   int(capacity.group(1).replace(".", "")) if capacity else None)


def _int(cell: str) -> int:
    value = _text(cell)
    return int(value) if value.isdigit() else 0


def parse_player(page: str, ogol_id: int) -> RawPlayer:
    cards = _cards(page)
    birth = re.match(r"(\d{4}-\d{2}-\d{2})", cards.get("Data de Nascimento", ""))
    # "Altura / Peso": "188 cm / 84 kg"; or "Altura": "187 cm" and "Peso": "80 kg" apart
    size = re.match(r"(\d+)\s*cm(?:\s*/\s*(\d+)\s*kg)?",
                    cards.get("Altura / Peso") or cards.get("Altura", ""))
    weight = re.match(r"(\d+)\s*kg", cards.get("Peso", ""))
    career: list[SeasonLine] = []
    table = ""
    if 'class="career"' in page:
        table = page.split('class="career"', 1)[1].split("</table>", 1)[0]
    season = ""
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 6:
            continue
        season = _text(cells[1]) or season
        team = re.search(r"/equipe/[a-z0-9-]+/(\d+)", cells[2])
        path = re.search(r'href="(/equipe/[^"?]+)', cells[2])
        career.append(SeasonLine(season, int(team.group(1)) if team else None, _int(cells[3]),
                                 _int(cells[4]), _int(cells[5]), path.group(1) if path else ""))
    return RawPlayer(
        ogol_id=ogol_id, full_name=cards.get("Nome"),
        birth_date=birth.group(1) if birth else None,
        nationality=(cards.get("Nacionalidade")
                     or cards.get("Nacionalidade / Dupla Nacionalidade")),
        position=cards.get("Posição") or None,
        foot=FEET.get(cards.get("Pé preferencial", "")),
        height_cm=int(size.group(1)) if size else None,
        weight_kg=(int(size.group(2)) if size and size.group(2)
                   else int(weight.group(1)) if weight else None),
        career=tuple(career))
