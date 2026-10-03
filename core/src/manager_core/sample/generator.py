"""Deterministic fictional world generator (research R14, FR-024..028).

Same GENERATOR_VERSION + seed -> identical Dataset. All randomness comes from one
random.Random(seed), consumed in a fixed order (Constitution II). Changing anything here that
alters the output requires bumping GENERATOR_VERSION and regenerating data/sample.
"""

from __future__ import annotations

import dataclasses
import random
from datetime import date, timedelta

from manager_core.domain.attributes import (
    ALL_ATTRIBUTES,
    ATTRIBUTE_GROUPS,
    HIDDEN_ATTRIBUTES,
    AttributeGroup,
    Attributes,
)
from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset, Source
from manager_core.domain.player import Player
from manager_core.domain.positions import Position, PositionFamiliarity
from manager_core.domain.squad import SquadMembership
from manager_core.io.schema import FORMAT_VERSION
from manager_core.ratings.ability import current_ability
from manager_core.ratings.suitability import position_weights
from manager_core.sample.names import (
    CLUBS,
    FIRST_NAMES,
    FOREIGN_NATIONS,
    NICKNAMES,
    SECOND_NATIONALITIES,
    SURNAMES,
    ClubIdentity,
)

GENERATOR_VERSION = "1.1.1"  # 1.1: Brazilian shirt numbers by ability; 1.1.1: notes text
TOOL = "manager_core.sample"
REFERENCE_DATE = date(2027, 1, 1)
GENERATED_ON = date(2026, 10, 2)

TIER_QUALITY = {"strong": 13.5, "mid": 10.0, "small": 8.0}

# 27 players: 3 GK, 8 DEF, 8 MID, 8 ATT
SQUAD_SHAPE: tuple[Position, ...] = (
    (Position.GK,) * 3
    + (Position.DC,) * 4 + (Position.DL,) * 2 + (Position.DR,) * 2
    + (Position.DM,) * 2 + (Position.MC,) * 4 + (Position.ML, Position.MR)
    + (Position.AML, Position.AMR) + (Position.AMC,) * 2 + (Position.ST,) * 4
)

# Typical secondary positions (familiarity ranges), FM-style
SECONDARY: dict[Position, tuple[tuple[Position, int, int], ...]] = {
    Position.GK: (),
    Position.DC: ((Position.DM, 6, 13), (Position.DR, 4, 10)),
    Position.DL: ((Position.WBL, 14, 17), (Position.ML, 8, 13), (Position.DC, 5, 11)),
    Position.DR: ((Position.WBR, 14, 17), (Position.MR, 8, 13), (Position.DC, 5, 11)),
    Position.DM: ((Position.MC, 12, 17), (Position.DC, 6, 13)),
    Position.MC: ((Position.DM, 10, 16), (Position.AMC, 9, 15)),
    Position.ML: ((Position.AML, 13, 17), (Position.WBL, 7, 13), (Position.MR, 6, 12)),
    Position.MR: ((Position.AMR, 13, 17), (Position.WBR, 7, 13), (Position.ML, 6, 12)),
    Position.AML: ((Position.ML, 12, 17), (Position.AMR, 9, 15), (Position.ST, 6, 12)),
    Position.AMR: ((Position.MR, 12, 17), (Position.AML, 9, 15), (Position.ST, 6, 12)),
    Position.AMC: ((Position.MC, 10, 16), (Position.ST, 7, 13)),
    Position.ST: ((Position.AMC, 6, 13), (Position.AML, 4, 10)),
}

HEIGHT_BY_POSITION = {
    Position.GK: (189, 4), Position.DC: (186, 4), Position.DL: (176, 5), Position.DR: (176, 5),
    Position.DM: (180, 5), Position.MC: (177, 5), Position.ML: (173, 5), Position.MR: (173, 5),
    Position.AML: (172, 5), Position.AMR: (172, 5), Position.AMC: (175, 5), Position.ST: (182, 6),
}

LEFT_SIDED = {Position.DL, Position.WBL, Position.ML, Position.AML}
PHYSICAL_DECLINE = ("pace", "acceleration", "stamina", "agility", "natural_fitness")
HEIGHT_LINKED = ("jumping_reach", "heading", "strength", "aerial_reach")
GK_LOW_OUTFIELD = ("finishing", "dribbling", "crossing", "long_shots", "tackling", "marking",
                   "heading", "off_the_ball", "flair")


def _clamp(value: float, lo: int = 1, hi: int = 20) -> int:
    return max(lo, min(hi, round(value)))


def _age(rng: random.Random) -> int:
    return _clamp(rng.gauss(26, 4.2), 17, 36)


def _attributes(rng: random.Random, position: Position, quality: float, age: int,
                height: int) -> Attributes:
    q = rng.gauss(quality, 1.0) - max(0, 22 - age) * 0.35  # youngsters are not finished yet
    values: dict[str, float] = {n: rng.gauss(q - 3, 1.8) for n in ALL_ATTRIBUTES}
    for name, weight in position_weights()[position].items():
        values[name] = rng.gauss(q + 0.9 * weight, 1.4)

    gk_names = ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]
    if position is Position.GK:
        for name in gk_names:
            if name not in position_weights()[Position.GK]:
                values[name] = rng.gauss(q - 1, 2.0)
        for name in GK_LOW_OUTFIELD:
            values[name] = min(10.0, rng.gauss(4, 2))
    else:
        for name in gk_names:
            values[name] = min(5.0, rng.gauss(2, 1))

    shift = (height - 180) / 6
    for name in HEIGHT_LINKED:
        values[name] += shift
    if age > 30:
        for name in PHYSICAL_DECLINE:
            values[name] -= (age - 30) * 0.5
    if age >= 34:
        for name in ("pace", "acceleration"):
            values[name] = min(values[name], 16.0)

    values["dirtiness"] = rng.gauss(8, 3.5)
    values["injury_proneness"] = rng.gauss(8, 3.5)
    values["controversy"] = rng.gauss(6, 3.5)
    for name in HIDDEN_ATTRIBUTES:
        if name not in ("dirtiness", "injury_proneness", "controversy"):
            values[name] = rng.gauss(10, 3.5)
    return Attributes(**{n: _clamp(values[n]) for n in ALL_ATTRIBUTES})


def _positions(rng: random.Random, main: Position) -> PositionFamiliarity:
    familiarity = {main: rng.choice((18, 19, 20, 20, 20))}
    for pos, lo, hi in SECONDARY[main]:
        familiarity[pos] = rng.randint(lo, hi)
    return PositionFamiliarity(familiarity)


def _feet(rng: random.Random, position: Position) -> tuple[int, int]:
    roll = rng.random()
    if roll < 0.05:
        return rng.randint(16, 20), rng.randint(16, 20)
    left_prob = 0.55 if position in LEFT_SIDED else 0.15
    weak = rng.randint(4, 12)
    return (20, weak) if rng.random() < left_prob else (weak, 20)


def _nationalities(rng: random.Random) -> tuple[str, ...]:
    roll = rng.random()
    if roll < 0.05:
        return (rng.choice(FOREIGN_NATIONS),)
    if roll < 0.07:
        return ("BRA", rng.choice(SECOND_NATIONALITIES))
    return ("BRA",)


def _names(rng: random.Random) -> tuple[str, str]:
    first = rng.choice(FIRST_NAMES)
    surname = rng.choice(SURNAMES)
    full = f"{first} {surname}"
    if rng.random() < 0.5:
        full = f"{first} {rng.choice(SURNAMES)} {surname}"
    roll = rng.random()
    if roll < 0.40:
        display = first
    elif roll < 0.65:
        display = surname
    elif roll < 0.85:
        display = rng.choice(NICKNAMES)
    else:
        display = f"{first} {surname}"
    return full, display


def _potential(rng: random.Random, ca: int, age: int) -> int:
    if age <= 21:
        headroom = rng.randint(15, 45)
    elif age <= 24:
        headroom = rng.randint(5, 25)
    elif age <= 28:
        headroom = rng.randint(0, 10)
    else:
        headroom = rng.randint(0, 3)
    return min(200, ca + headroom)


def make_player(rng: random.Random, pid: str, position: Position, quality: float,
                reference_date: date = REFERENCE_DATE, age: int | None = None) -> Player:
    """One generated player. With the defaults this is exactly the sample world's player
    (same RNG consumption); careers pass their own date and an age (e.g. youngsters, spec 004)."""
    if age is None:
        age = _age(rng)
    born = reference_date - timedelta(days=age * 365 + rng.randint(30, 330) + age // 4)
    height_mu, height_sd = HEIGHT_BY_POSITION[position]
    height = _clamp(rng.gauss(height_mu, height_sd), 160, 205)
    weight = _clamp(height - 104 + rng.gauss(0, 4), 55, 100)
    full_name, display_name = _names(rng)
    left, right = _feet(rng, position)
    player = Player(
        id=pid,
        full_name=full_name,
        display_name=display_name,
        date_of_birth=born,
        nationalities=_nationalities(rng),
        height_cm=height,
        weight_kg=weight,
        left_foot=left,
        right_foot=right,
        attributes=_attributes(rng, position, quality, age, height),
        positions=_positions(rng, position),
        potential_ability=200,  # replaced below once CA is known
    )
    return dataclasses.replace(
        player, potential_ability=_potential(rng, current_ability(player), age)
    )


def _player(rng: random.Random, pid: str, position: Position, quality: float) -> Player:
    return make_player(rng, pid, position, quality)


def make_club(identity: ClubIdentity, state: str = "MG") -> Club:
    return _club(identity, state)


def _club(identity: ClubIdentity, state: str = "MG") -> Club:
    return Club(
        id=identity.id,
        name=identity.name,
        short_name=identity.short_name,
        abbreviation=identity.abbreviation,
        city=identity.city,
        state=state,
        country="BRA",
        color_primary=identity.color_primary,
        color_secondary=identity.color_secondary,
        stadium_name=identity.stadium_name,
        stadium_capacity=identity.stadium_capacity,
        founded_year=identity.founded_year,
        reputation=identity.reputation,
    )


# Traditional Brazilian numbering: 2 LD, 3/4 ZAG, 5 VOL, 6 LE, 7/11 wingers, 8 MC, 9 ATA, 10 MEI.
# The first free preferred number wins; squad players fall back to the lowest free number >= 13.
PREFERRED_NUMBERS: dict[Position, tuple[int, ...]] = {
    Position.GK: (1, 12, 23),
    Position.DR: (2, 13),
    Position.DC: (3, 4, 14, 15),
    Position.DL: (6, 16),
    Position.DM: (5, 17),
    Position.MC: (8, 18, 20, 25),
    Position.MR: (7,),
    Position.ML: (11,),
    Position.AMR: (7, 19),
    Position.AML: (11, 21),
    Position.AMC: (10, 22),
    Position.ST: (9, 19, 24, 26),
}


def assign_shirt_numbers(squad: list[tuple[Position, Player]]) -> list[int]:
    """Brazilian shirt numbers for a new squad (used by careers for promoted clubs)."""
    return _shirt_numbers(squad)


def _shirt_numbers(squad: list[tuple[Position, Player]]) -> list[int]:
    """One number per squad entry. Better players (by CA) pick first, so the 9 is the
    first-choice striker and shared numbers (7, 11) go to the best winger or wide midfielder."""
    order = sorted(
        range(len(squad)), key=lambda i: (-current_ability(squad[i][1]), squad[i][1].id)
    )
    taken: set[int] = set()
    numbers = [0] * len(squad)
    for i in order:
        position = squad[i][0]
        choice = next((n for n in PREFERRED_NUMBERS[position] if n not in taken), None)
        if choice is None:
            choice = next(n for n in range(13, 100) if n not in taken)
        taken.add(choice)
        numbers[i] = choice
    return numbers


def generate(seed: int = 20261002) -> Dataset:
    rng = random.Random(seed)
    clubs: dict[str, Club] = {}
    players: dict[str, Player] = {}
    memberships: dict[str, SquadMembership] = {}
    counter = 0
    for identity in CLUBS:
        clubs[identity.id] = _club(identity)
        quality = TIER_QUALITY[identity.tier]
        squad: list[tuple[Position, Player]] = []
        for position in SQUAD_SHAPE:
            counter += 1
            pid = f"p-{counter:06d}"
            squad.append((position, _player(rng, pid, position, quality)))
        for (_, player), number in zip(squad, _shirt_numbers(squad), strict=True):
            players[player.id] = player
            memberships[player.id] = SquadMembership(player.id, identity.id, shirt_number=number)
    return Dataset(
        format_version=FORMAT_VERSION,
        reference_date=REFERENCE_DATE,
        fictional=True,
        tool=TOOL,
        tool_version=GENERATOR_VERSION,
        seed=seed,
        notes="Mundo fictício no estilo do futebol mineiro: 12 clubes, sem clubes/pessoas reais.",
        sources=(Source(name=f"{TOOL} {GENERATOR_VERSION}", retrieved_on=GENERATED_ON),),
        clubs=clubs,
        players=players,
        memberships=memberships,
    )
