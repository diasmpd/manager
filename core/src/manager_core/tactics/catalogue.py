"""Tactical options, roles and suggestions as reference data (spec 006 FR-002, research R1, R4)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from manager_core.domain.player import Player
from manager_core.domain.positions import Position

IP = "ip"
OOP = "oop"


@dataclass(frozen=True, slots=True)
class OptionDef:
    id: str
    phase: str
    label: str
    settings: tuple[str, ...]
    labels: tuple[str, ...]
    default: str


@dataclass(frozen=True, slots=True)
class Options:
    mentality: OptionDef
    team: tuple[OptionDef, ...]
    player: tuple[OptionDef, ...]
    takers: tuple[str, ...]
    taker_labels: tuple[str, ...]
    setups: tuple[OptionDef, ...]

    def team_option(self, option_id: str) -> OptionDef | None:
        return next((o for o in self.team if o.id == option_id), None)

    def player_option(self, option_id: str) -> OptionDef | None:
        return next((o for o in self.player if o.id == option_id), None)

    def setup_option(self, option_id: str) -> OptionDef | None:
        return next((o for o in self.setups if o.id == option_id), None)


@dataclass(frozen=True, slots=True)
class Role:
    id: str
    phase: str  # ip / oop
    label: str
    positions: tuple[Position, ...]
    key: dict[str, float]
    locked: dict[str, str]
    levers: dict[str, float]


@dataclass(frozen=True, slots=True)
class Roles:
    roles: dict[str, Role]
    defaults: dict[Position, tuple[str, str]]
    oop_suggestions: dict[str, tuple[str, ...]]


def _read(name: str) -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("tactics").joinpath(name)
    return tomllib.loads(entry.read_text("utf-8"))


def _option(raw: dict[str, Any], default: str | None = None) -> OptionDef:
    settings = tuple(raw["settings"])
    return OptionDef(raw.get("id", ""), raw.get("phase", ""), raw["label"], settings,
                     tuple(raw["labels"]), raw.get("default", default or settings[0]))


@cache
def load_options() -> Options:
    doc = _read("options.toml")
    sp = doc["set_pieces"]
    return Options(
        mentality=_option({**doc["mentality"], "id": "mentality"}),
        team=tuple(_option(o) for o in doc["team"]),
        player=tuple(_option(o) for o in doc["player"]),
        takers=tuple(sp["takers"]), taker_labels=tuple(sp["taker_labels"]),
        setups=tuple(_option(o) for o in sp["setups"]),
    )


@cache
def load_roles() -> Roles:
    doc = _read("roles.toml")
    roles = {
        r["id"]: Role(r["id"], r["phase"], r["label"],
                      tuple(Position(p) for p in r["positions"]),
                      {k: float(v) for k, v in r["key"].items()},
                      dict(r.get("locked", {})),
                      {k: float(v) for k, v in r.get("levers", {}).items()})
        for r in doc["roles"]
    }
    defaults = {Position(pos): (ip, oop) for pos, (ip, oop) in doc["defaults"].items()}
    suggestions = {name: tuple(s) for name, s in doc["oop_suggestions"].items()}
    return Roles(roles, defaults, suggestions)


def valid_roles(position: Position, phase: str) -> list[Role]:
    return [r for r in load_roles().roles.values()
            if r.phase == phase and position in r.positions]


def suggest_oop(ip_formation: str) -> tuple[str, ...]:
    """FM26 suggests three out-of-possession shapes for an in-possession formation."""
    return load_roles().oop_suggestions.get(ip_formation, (ip_formation,) * 3)


def role_suitability(player: Player, role: Role) -> float:
    """Weighted mean of the role's key attributes, on the 1-20 scale."""
    total = sum(role.key.values())
    return sum(player.attributes.get(name) * w for name, w in role.key.items()) / total
