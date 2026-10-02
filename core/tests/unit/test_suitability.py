import pytest

from manager_core.domain.positions import Position
from manager_core.ratings.suitability import base, position_weights, suitability, suitability_milli
from tests.helpers import attrs, player


def test_weights_cover_all_positions_and_mirror() -> None:
    weights = position_weights()
    assert set(weights) == set(Position)
    for left, right in [("DL", "DR"), ("WBL", "WBR"), ("ML", "MR"), ("AML", "AMR")]:
        assert weights[Position(left)] == weights[Position(right)]


def test_base_is_weighted_mean_of_key_attributes() -> None:
    dc_keys = position_weights()[Position.DC]
    p = player(attributes=attrs(5, **dict.fromkeys(dc_keys, 15)))
    assert base(p, Position.DC) == pytest.approx(15)
    assert base(p, Position.ST) < 15


def test_uniform_player_has_uniform_base() -> None:
    p = player(attributes=attrs(12))
    assert all(base(p, pos) == pytest.approx(12) for pos in Position)


def test_familiarity_penalises() -> None:
    natural = player("p-a", positions={Position.DC: 20})
    unconvincing = player("p-b", positions={Position.MC: 20, Position.DC: 10})
    assert suitability(natural, Position.DC) > suitability(unconvincing, Position.DC)


def test_mirrored_players_are_equal() -> None:
    left = player("p-a", positions={Position.DL: 20})
    right = player("p-b", positions={Position.DR: 20})
    assert suitability(left, Position.DL) == suitability(right, Position.DR)


def test_milli_is_int() -> None:
    p = player(positions={Position.DC: 17}, attributes=attrs(13))
    value = suitability_milli(p, Position.DC)
    assert isinstance(value, int)
    assert value == round(suitability(p, Position.DC) * 1000)
