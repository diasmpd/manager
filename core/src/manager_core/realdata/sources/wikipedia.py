"""pt.wikipedia club pages (spec 011 R1/R3): the infobox's identity facts. Wikipedia is the first
source for a club's name, city and founding year; ogol's exact capacity and full stadium name
are kept when Wikipedia's are rounded or short, and real disagreements go to the import report.
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass
from urllib.parse import quote

BASE = "https://pt.wikipedia.org/wiki/"


@dataclass(frozen=True, slots=True)
class WikiClub:
    name: str | None
    founded: int | None  # the first founding year
    city: str | None
    stadium: str | None
    capacity: int | None
    capacity_exact: bool  # False for a rounded "62 mil"


def url(title: str) -> str:
    return BASE + quote(title.replace(" ", "_"))


def _text(fragment: str) -> str:
    fragment = re.sub(r'<sup[^>]*class="reference[^"]*".*?</sup>', " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _rows(page: str) -> dict[str, str]:
    """Infobox label -> the row's raw data cell (the first one wins)."""
    start = page.find('class="infobox')
    box = page[start:page.find("</table>", start)] if start >= 0 else ""
    out: dict[str, str] = {}
    for label, data in re.findall(r'<th[^>]*class="infobox-label"[^>]*>(.*?)</th>\s*'
                                  r'<td[^>]*class="infobox-data"[^>]*>(.*?)</td>', box, re.S):
        out.setdefault(_text(label), data)
    return out


def capacity(text: str) -> tuple[int | None, bool]:
    """'23 018', '23.018' or '61 846' -> exact; '62 mil' -> 62000, rounded."""
    text = text.replace("\xa0", " ").replace(" ", " ")
    rounded = re.match(r"(\d+(?:[.,]\d+)?)\s*mil\b", text)
    if rounded:
        return round(float(rounded.group(1).replace(",", ".")) * 1000), False
    exact = re.match(r"(\d{1,3}(?:[ .]\d{3})+|\d+)", text)
    if exact:
        return int(re.sub(r"[ .]", "", exact.group(1))), True
    return None, False


def parse_club(page: str) -> WikiClub:
    rows = _rows(page)
    founded = None
    birth = re.search(r'class="bday[^"]*">(\d{4})-\d{2}-\d{2}<', rows.get("Fundação", ""))
    if birth:
        founded = int(birth.group(1))
    else:
        year = re.search(r"\b(1[89]\d{2}|20\d{2})\b", _text(rows.get("Fundação", "")))
        founded = int(year.group(1)) if year else None
    place = _text(rows.get("Localização", ""))
    size, exact = capacity(_text(rows.get("Capacidade", "")))
    return WikiClub(
        name=_text(rows["Nome"]) or None if "Nome" in rows else None,
        founded=founded,
        city=place.split(",")[0].strip() or None if place else None,
        stadium=_text(rows["Estádio"]) or None if "Estádio" in rows else None,
        capacity=size, capacity_exact=exact)
