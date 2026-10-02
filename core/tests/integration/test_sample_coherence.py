"""SC-005 / FR-026: sample players look like football players for their positions."""

from pathlib import Path
from statistics import mean

import pytest

from manager_core import api
from manager_core.domain.attributes import ATTRIBUTE_GROUPS, HIDDEN_ATTRIBUTES, AttributeGroup
from manager_core.domain.dataset import Dataset
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.ratings.ability import best_position, current_ability, is_goalkeeper
from manager_core.ratings.suitability import position_weights


@pytest.fixture(scope="module")
def world() -> Dataset:
    sample = Path(__file__).resolve().parents[3] / "data" / "sample"
    dataset = api.load_dataset(sample).dataset
    assert dataset is not None
    return dataset


def _key_mean(p: Player, position: Position) -> float:
    weights = position_weights()[position]
    return sum(p.attributes.get(n) * w for n, w in weights.items()) / sum(weights.values())


def test_key_attributes_beat_other_lines(world: Dataset) -> None:
    players = list(world.players.values())
    checked = 0
    for position in Position:
        naturals = [p for p in players if p.positions[position] >= 18]
        others = [p for p in players if best_position(p).line is not position.line]
        if not naturals:
            continue
        checked += 1
        gap = mean(_key_mean(p, position) for p in naturals) - mean(
            _key_mean(p, position) for p in others
        )
        assert gap >= 2, (position, round(gap, 2))
    assert checked >= 10


def test_goalkeepers_are_goalkeepers(world: Dataset) -> None:
    gk_names = ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]
    gks = [p for p in world.players.values() if is_goalkeeper(p)]
    outfield = [p for p in world.players.values() if not is_goalkeeper(p)]

    def gk_mean(group: list[Player]) -> float:
        return mean(mean(p.attributes.get(n) for n in gk_names) for p in group)

    assert gk_mean(gks) - gk_mean(outfield) >= 8


def test_hidden_attributes_vary(world: Dataset) -> None:
    for p in world.players.values():
        assert len({p.attributes.get(n) for n in HIDDEN_ATTRIBUTES}) > 1, p.id


def test_tier_quality_order(world: Dataset) -> None:
    def tier_ca(lo: int, hi: int) -> float:
        clubs = [c for c in world.clubs.values() if lo <= c.reputation <= hi]
        return mean(current_ability(p) for c in clubs for p in world.squad(c.id))

    assert tier_ca(13, 15) > tier_ca(9, 11) > tier_ca(6, 8)
