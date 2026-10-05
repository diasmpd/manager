"""Tactics as quick-sim levers (spec 006 FR-005, research R2, R3).

`levers(own, opponent)` combines one side's mentality, team instructions, roles, player
instructions and set-piece setups, plus the interaction rules against the opponent's tactic,
into a small set of multipliers the engine understands. Neutral settings give all 1.0
(possession: +0). Sizes are data (`reference/tactics/effects.toml`).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from functools import cache
from importlib import resources
from typing import Any

from manager_core.tactics.catalogue import load_options, load_roles
from manager_core.tactics.model import Tactic

LEVER_MIN, LEVER_MAX = 0.6, 1.5
PLAYERS = 11
# A lever is "good" for the side when it moves in this direction (used by tests and reports).
GOOD_UP = {"shot_rate", "chance_quality", "possession", "counter", "set_piece"}
GOOD_DOWN = {"allow_rate", "allow_quality", "foul_rate", "card_rate", "fatigue", "error_risk"}


@dataclass(frozen=True, slots=True)
class Levers:
    shot_rate: float = 1.0
    chance_quality: float = 1.0
    allow_rate: float = 1.0
    allow_quality: float = 1.0
    possession: float = 0.0  # additive percentage points
    foul_rate: float = 1.0
    card_rate: float = 1.0
    fatigue: float = 1.0
    set_piece: float = 1.0
    counter: float = 1.0
    error_risk: float = 1.0


NEUTRAL = Levers()
NAMES = tuple(f.name for f in fields(Levers))


@cache
def effects_table() -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("tactics").joinpath("effects.toml")
    return tomllib.loads(entry.read_text("utf-8"))


class _Acc:
    def __init__(self) -> None:
        self.values = {n: (0.0 if n == "possession" else 1.0) for n in NAMES}

    def apply(self, changes: dict[str, float], share: float = 1.0) -> None:
        for name, value in changes.items():
            if name == "possession":
                self.values[name] += float(value) * share
            else:
                self.values[name] *= float(value) ** share

    def levers(self) -> Levers:
        out = {n: (v if n == "possession" else min(LEVER_MAX, max(LEVER_MIN, v)))
               for n, v in self.values.items()}
        return Levers(**out)


def _matches(rule: dict[str, list[str]], tactic: Tactic) -> bool:
    team = dict(tactic.team)
    return all(team.get(option) in settings for option, settings in rule.items())


def levers(own: Tactic, opponent: Tactic | None = None, flank_balance: float = 0.0) -> Levers:
    """The side's levers. `flank_balance` in [-1, 1]: >0 when the opponent's right flank is
    weaker than its left (so progressing through our left pays off), <0 the other way."""
    table = effects_table()
    acc = _Acc()
    step = load_options().mentality.settings.index(own.mentality) - 3
    if step:
        acc.apply({n: (v * step if n == "possession" else 1 + v * step)
                   for n, v in table["mentality_step"].items()})
    team_effects = table["team"]
    for option, setting in own.team:
        acc.apply(team_effects.get(option, {}).get(setting, {}))
    direction = dict(own.team).get("progress_through", "balanced")
    if direction != "balanced":
        sign = 1 if direction == "left" else -1
        acc.apply({"chance_quality": 1 + table["context"]["flank_bonus"] * sign * flank_balance})
    roles = load_roles().roles
    player_effects = table["player"]
    for slot in own.slots:
        for role_id in (slot.ip_role, slot.oop_role):
            role = roles.get(role_id)
            if role is not None:  # a role is one player's job: same share as his instructions
                acc.apply(role.levers, share=1 / PLAYERS)
        for instr, setting in slot.instructions:
            acc.apply(player_effects.get(instr, {}).get(setting, {}), share=1 / PLAYERS)
    for setup, setting in own.set_pieces.setups:
        acc.apply(table["setup"].get(setup, {}).get(setting, {}))
    if opponent is not None:
        for rule in table["interactions"]:
            if _matches(rule["own"], own) and _matches(rule["opponent"], opponent):
                acc.apply(rule["levers"])
    return acc.levers()


def option_effect(option: str, setting: str, section: str = "team") -> dict[str, float]:
    """The documented lever changes of one setting (section: team, player or setup)."""
    return dict(effects_table()[section].get(option, {}).get(setting, {}))
