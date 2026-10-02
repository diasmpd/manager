"""Position suitability (research R7): weighted mean of the position's key attributes
(reference/position_weights.csv), scaled by the FM familiarity penalty."""

from __future__ import annotations

from functools import cache
from importlib import resources

from manager_core.domain.player import Player
from manager_core.domain.positions import Position, familiarity_factor
from manager_core.io.dialect import read_text_table

_MIRRORS = {
    Position.DR: Position.DL,
    Position.WBR: Position.WBL,
    Position.MR: Position.ML,
    Position.AMR: Position.AML,
}


@cache
def position_weights() -> dict[Position, dict[str, float]]:
    text = (
        resources.files("manager_core.reference")
        .joinpath("position_weights.csv")
        .read_text("utf-8-sig")
    )
    weights: dict[Position, dict[str, float]] = {}
    for row in read_text_table(text).rows:
        v = row.values
        weights.setdefault(Position(v["position"]), {})[v["attribute"]] = float(v["weight"])
    for right, left in _MIRRORS.items():
        weights[right] = weights[left]
    return {p: weights[p] for p in Position}


def base(player: Player, position: Position) -> float:
    """Weighted mean of the position's key attributes, on the 1-20 scale."""
    weights = position_weights()[position]
    total = sum(player.attributes.get(name) * w for name, w in weights.items())
    return total / sum(weights.values())


def suitability(player: Player, position: Position) -> float:
    return base(player, position) * familiarity_factor(player.positions[position])


def suitability_milli(player: Player, position: Position) -> int:
    """Integer score used for rankings and lineup assignment (exact, machine-independent ties)."""
    return round(suitability(player, position) * 1000)
