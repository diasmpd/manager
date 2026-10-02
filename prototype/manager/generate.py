"""Generates fictional, position-coherent squads so the engine can run without a real database."""
from __future__ import annotations

import random

from .models import GOALKEEPING, HIDDEN, POSITION_WEIGHTS, Attributes, Player, Team
from .tactics import Tactic

FIRST = ["João", "Pedro", "Lucas", "Gabriel", "Rafael", "Bruno", "Thiago", "Diego", "Caio", "Felipe",
         "Matheus", "Vinícius", "André", "Igor", "Renan", "Wesley", "Everton", "Danilo", "Hugo", "Léo",
         "Marcos", "Rodrigo", "Gustavo", "Alex", "Fábio", "Murilo", "Kaio", "Douglas", "Otávio", "Emerson"]
LAST = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Rodrigues", "Almeida", "Nunes",
        "Carvalho", "Gomes", "Ribeiro", "Martins", "Rocha", "Barbosa", "Teixeira", "Moura", "Cardoso", "Freitas",
        "Araújo", "Mendes", "Batista", "Ramos", "Vieira", "Monteiro", "Pinto", "Correia", "Dias", "Farias"]

# 25-man squad: main position of each player
SQUAD_POSITIONS = ["GK"] * 3 + ["DC"] * 4 + ["DL"] * 2 + ["DR"] * 2 + ["DM"] * 2 + ["MC"] * 4 + \
                  ["ML", "AML", "MR", "AMR", "AMC"] + ["ST"] * 3

SECONDARY = {
    "GK": {}, "DC": {"DM": 9}, "DL": {"WBL": 17, "ML": 10}, "DR": {"WBR": 17, "MR": 10},
    "DM": {"MC": 15, "DC": 10}, "MC": {"DM": 13, "AMC": 12}, "ML": {"AML": 17, "WBL": 9, "MR": 8},
    "MR": {"AMR": 17, "WBR": 9, "ML": 8}, "AML": {"ML": 16, "AMR": 12, "ST": 8},
    "AMR": {"MR": 16, "AML": 12, "ST": 8}, "AMC": {"MC": 13, "ST": 10}, "ST": {"AMC": 9},
}


def _clamp(v: float) -> int:
    return max(1, min(20, round(v)))


def make_player(rng: random.Random, position: str, quality: float, used_names: set[str]) -> Player:
    q = rng.gauss(quality, 1.2)   # individual quality around the team's level
    values = {name: _clamp(rng.gauss(q - 2.5, 2.3)) for name in Attributes.names()}
    for name, weight in POSITION_WEIGHTS[position].items():
        values[name] = _clamp(rng.gauss(q + 0.8 * weight, 1.8))
    if position == "GK":
        for name in ("finishing", "dribbling", "crossing", "heading", "long_shots", "tackling", "marking"):
            values[name] = _clamp(rng.gauss(4, 2))
    else:
        for name in GOALKEEPING:
            values[name] = _clamp(rng.gauss(2, 1))
    for name in HIDDEN:
        values[name] = _clamp(rng.gauss(10, 3.5))
    values["aggression"] = _clamp(rng.gauss(11 if position in ("DC", "DM") else 9, 3.5))
    values["temperament"] = _clamp(rng.gauss(11, 3.5))

    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    while name in used_names:
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    used_names.add(name)
    positions = {position: 20, **SECONDARY[position]}
    return Player(name=name, positions=positions, attrs=Attributes(**values), age=rng.randint(18, 34))


def make_team(name: str, quality: float = 11, seed: int | None = None, tactic: Tactic | None = None) -> Team:
    """quality ~ level of key attributes: 8 = weak Série D side, 11 = mid Série A, 14 = title contender."""
    rng = random.Random(seed)
    used: set[str] = set()
    squad = [make_player(rng, pos, quality, used) for pos in SQUAD_POSITIONS]
    return Team(name=name, squad=squad, tactic=tactic or Tactic(), reputation=_clamp(quality))
