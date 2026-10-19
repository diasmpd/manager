"""Source vocabulary -> game values (spec 011 R3/R4): ogol position labels to FM positions, PT-BR
nation names to the game's codes, and the preferred foot to the two foot ratings.
"""

from __future__ import annotations

import csv
import hashlib
from functools import cache
from importlib import resources

from manager_core.domain.positions import Position

NATURAL = 20  # the first position ogol lists
SECOND = 16  # every further listed position (accomplished)
WING_BACK = 14  # a full-back's wing-back slot: close, but not a listed position

# ogol labels, longest first so "Meia Ofensivo" wins over "Meia"
LABELS: tuple[tuple[str, Position], ...] = tuple(sorted({
    "Goleiro": Position.GK,
    "Zagueiro": Position.DC,
    "Defesa Central": Position.DC,
    "Defensor": Position.DC,
    "Lateral Esquerdo": Position.DL,
    "Lateral Direito": Position.DR,
    "Ala Esquerdo": Position.WBL,
    "Ala Direito": Position.WBR,
    "Volante": Position.DM,
    "Meia Central": Position.MC,
    "Meia": Position.MC,
    "Meio-campista": Position.MC,
    "Meia Esquerda": Position.ML,
    "Meia Direita": Position.MR,
    "Meia Ofensivo": Position.AMC,
    "Ponta Esquerda": Position.AML,
    "Ponta Direita": Position.AMR,
    "Centroavante": Position.ST,
    "2º Atacante": Position.ST,
    "Atacante": Position.ST,
}.items(), key=lambda item: -len(item[0])))

# the squad section, when the player page lists no position
GROUP_POSITION = {"GK": Position.GK, "D": Position.DC, "M": Position.MC, "A": Position.ST}
WING_BACKS = {Position.DL: Position.WBL, Position.DR: Position.WBR}


def positions_from_label(label: str | None) -> list[Position]:
    """'Ponta Direita Meia Ofensivo' -> [AMR, AMC], in ogol's order, without repeats."""
    found: list[Position] = []
    rest = (label or "").strip()
    while rest:
        for text, position in LABELS:
            if rest.startswith(text):
                if position not in found:
                    found.append(position)
                rest = rest[len(text):].strip()
                break
        else:  # an unknown word: skip it
            rest = rest.partition(" ")[2].strip()
    return found


def familiarity(positions: list[Position]) -> dict[Position, int]:
    out: dict[Position, int] = {}
    for i, position in enumerate(positions):
        out[position] = NATURAL if i == 0 else SECOND
    for back, wing in WING_BACKS.items():
        if back in out and wing not in out:
            out[wing] = WING_BACK
    return out


@cache
def _nation_codes() -> dict[str, str]:
    text = resources.files("manager_core.reference").joinpath("nations.csv").read_text("utf-8-sig")
    return {row["name_pt"].casefold(): row["code"] for row in csv.DictReader(
        text.splitlines(), delimiter=";")}


def nations(text: str | None) -> tuple[tuple[str, ...], list[str]]:
    """'Brasil Itália' (ogol runs a dual nationality together) -> (('BRA', 'ITA'), []). Names are
    matched longest first ('Irlanda do Norte' before 'Irlanda'); unknown words come back in the
    second list."""
    names = sorted(_nation_codes(), key=len, reverse=True)
    codes: list[str] = []
    unknown: list[str] = []
    rest = (text or "").replace(",", " ").replace("/", " ").strip()
    while rest:
        folded = rest.casefold()
        name = next((n for n in names if folded.startswith(n)
                     and (len(folded) == len(n) or folded[len(n)] == " ")), None)
        if name is None:
            word, _, rest = rest.partition(" ")
            unknown.append(word)
        else:
            code = _nation_codes()[name]
            if code not in codes:
                codes.append(code)
            rest = rest[len(name):]
        rest = rest.strip()
    return tuple(codes[:3]), unknown


def feet(foot: str | None, player_id: str) -> tuple[int, int]:
    """(left, right). The weaker foot is 5-12, fixed per player id."""
    weak = 5 + int(hashlib.sha1(f"foot:{player_id}".encode()).hexdigest(), 16) % 8
    if foot == "left":
        return 20, weak
    if foot == "both":
        return 18, 18
    return weak, 20
