"""The attribute-synthesis model (spec 011 R4): public signals -> a target Current Ability ->
the full attribute set, generated from the position's own weights and nudged until the game's
`current_ability` formula gives the target. No other game's ratings are an input (owner
decision 1, 2026-10-07).
"""

from __future__ import annotations

import math
import random
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from manager_core.domain.attributes import (
    ATTRIBUTE_GROUPS,
    HIDDEN_DEFAULTS,
    MAX_VALUE,
    MIN_VALUE,
    AttributeGroup,
)
from manager_core.domain.positions import Position
from manager_core.ratings.ability import GENERAL_SHARE, KEY_SHARE
from manager_core.ratings.suitability import position_weights

ATTACKING = frozenset({Position.ST, Position.AMC, Position.AML, Position.AMR})
_OUTFIELD_GENERAL = (ATTRIBUTE_GROUPS[AttributeGroup.TECHNICAL]
                     + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
                     + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL])
_GK_GENERAL = (ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]
               + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
               + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL])
_VISIBLE = tuple(n for g, names in ATTRIBUTE_GROUPS.items() if g is not AttributeGroup.HIDDEN
                 for n in names)


@cache
def params() -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("synthesis").joinpath("model.toml")
    return tomllib.loads(entry.read_text("utf-8"))


@dataclass(frozen=True, slots=True)
class Signals:
    """What public sources say about one player (any field may be unknown)."""

    player_id: str
    position: Position
    division: str  # A, B, C, D or none: the club's national division
    age: int | None = None
    games_share: float | None = None  # share of the club's games in the season, 0..1
    value_eur: int | None = None
    club_median_value_eur: float | None = None
    goals_per_game: float | None = None


@dataclass(frozen=True, slots=True)
class Synthesis:
    current_ability: int
    potential_ability: int
    attributes: dict[str, int]
    confidence: str  # high, medium, low
    reason: str


def target_ability(s: Signals) -> tuple[float, str, str]:
    """(CA, confidence, reason) from the signals."""
    p = params()
    o = p["offsets"]
    ca = float(p["division_ca"].get(s.division, p["division_ca"]["none"]))
    used: list[str] = [f"division {s.division}"]
    if s.games_share is not None:
        ca += o["games_share"] * (min(1.0, max(0.0, s.games_share)) - 0.5) * 2
        used.append("games")
    if s.value_eur and s.club_median_value_eur:
        ratio = math.log10(s.value_eur / s.club_median_value_eur)
        ca += o["value"] * max(-1.0, min(1.0, ratio))
        used.append("value")
    if s.goals_per_game is not None and s.position in ATTACKING:
        ca += o["attacking_output"] * min(0.6, s.goals_per_game) / 0.6 - o["attacking_output"] / 3
        used.append("goals")
    if s.age is not None:
        if s.age < o["age_peak_low"]:
            ca -= o["young_per_year"] * (o["age_peak_low"] - s.age)
        elif s.age > o["age_peak_high"]:
            ca -= o["old_per_year"] * (s.age - o["age_peak_high"])
    ca = max(o["min_ca"], min(o["max_ca"], ca))
    known = ("games" in used) + ("value" in used)
    confidence = "high" if known == 2 else "medium" if known == 1 else "low"
    return ca, confidence, ", ".join(used)


def _level(ca: float) -> float:
    """The position score that the game's formula maps to this CA (inverse of ability.py)."""
    return 1 + (ca - 1) * 19 / 199


def _score(attrs: dict[str, float], position: Position) -> float:
    weights = position_weights()[position]
    base = sum(attrs[n] * w for n, w in weights.items()) / sum(weights.values())
    general_names = _GK_GENERAL if position is Position.GK else _OUTFIELD_GENERAL
    general = sum(attrs[n] for n in general_names) / len(general_names)
    return KEY_SHARE * base + GENERAL_SHARE * general


def _age_shift(group: AttributeGroup, age: int | None) -> float:
    a = params()["attributes"]
    if age is None or group not in (AttributeGroup.PHYSICAL, AttributeGroup.MENTAL):
        return 0.0
    physical = group is AttributeGroup.PHYSICAL
    if age < 24:
        t = min(1.0, (24 - age) / 6)
        return t * float(a["young_physical"] if physical else a["young_mental"])
    if age > 29:
        t = min(1.0, (age - 29) / 6)
        return t * float(a["old_physical"] if physical else a["old_mental"])
    return 0.0


def attributes_for(position: Position, ca: float, age: int | None, seed: str) -> dict[str, int]:
    """Every attribute, so that the game's CA formula gives `ca` at `position`."""
    a = params()["attributes"]
    weights = position_weights()[position]
    top = max(weights.values())
    rng = random.Random(f"synthesis:{seed}")
    level = _level(ca)
    raw: dict[str, float] = {}
    for group, names in ATTRIBUTE_GROUPS.items():
        if group is AttributeGroup.HIDDEN:
            continue
        for name in names:
            # the position's key attributes above the level, the others below it
            shape = a["profile"] * weights[name] / top if name in weights else -a["off_profile"]
            if group is AttributeGroup.GOALKEEPING and position is not Position.GK:
                shape = -a["gk_outfield"]
            if position is Position.GK and group is AttributeGroup.TECHNICAL:
                shape = -a["gk_outfield"] if name not in weights else shape
            raw[name] = level + shape + _age_shift(group, age) + rng.gauss(0.0, a["spread"])
    for _ in range(6):  # nudge everything so the game's formula lands on the target
        clamped = {n: min(MAX_VALUE, max(MIN_VALUE, v)) for n, v in raw.items()}
        error = level - _score(clamped, position)
        if abs(error) < 0.02:
            break
        raw = {n: v + error for n, v in raw.items()}
    out = {n: min(MAX_VALUE, max(MIN_VALUE, round(v))) for n, v in raw.items()}
    out.update(HIDDEN_DEFAULTS)
    return out


def potential(ca: float, age: int | None) -> int:
    pot = params()["potential"]
    if age is None:
        room = pot["under_27"]
    elif age < 21:
        room = pot["under_21"]
    elif age < 24:
        room = pot["under_24"]
    elif age < 27:
        room = pot["under_27"]
    else:
        room = pot["over_27"]
    return round(min(200.0, ca + float(room)))


def synthesise(s: Signals) -> Synthesis:
    ca, confidence, reason = target_ability(s)
    attrs = attributes_for(s.position, ca, s.age, s.player_id)
    return Synthesis(round(ca), potential(ca, s.age), attrs, confidence, reason)
