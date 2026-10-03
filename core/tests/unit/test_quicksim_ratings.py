"""Team ratings from the players on the pitch (research R2)."""

import random

from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.quicksim.ratings import TeamRatings, rate
from tests.helpers import attrs, player

SLOTS = [Position.GK, Position.DL, Position.DC, Position.DC, Position.DR,
         Position.ML, Position.MC, Position.MC, Position.MR, Position.ST, Position.ST]


def _xi(**overrides: dict[str, int]) -> list[tuple[Position, Player]]:
    """An XI of natural players with all attributes 10; `overrides` maps slot index (as 's3')
    to attribute overrides."""
    xi = []
    for i, slot in enumerate(SLOTS):
        extra = overrides.get(f"s{i}", {})
        xi.append((slot, player(f"p{i:02d}", positions={slot: 20}, attributes=attrs(10, **extra))))
    return xi


def _rate(xi: list[tuple[Position, Player]]) -> TeamRatings:
    return rate(xi, SLOTS)


def test_composites_on_the_attribute_scale() -> None:
    r = _rate(_xi())
    for value in (r.attack, r.control, r.defence, r.goalkeeping, r.set_pieces, r.discipline):
        assert 1 <= value <= 20
    assert abs(r.attack - 10) < 0.01 and abs(r.defence - 10) < 0.01


def test_forward_finishing_raises_attack_not_defence() -> None:
    base = _rate(_xi())
    better = _rate(_xi(s9={"finishing": 20}))
    assert better.attack > base.attack
    assert better.defence == base.defence


def test_centre_back_tackling_raises_defence() -> None:
    base = _rate(_xi())
    better = _rate(_xi(s2={"tackling": 20}))
    assert better.defence > base.defence
    assert better.discipline < base.discipline  # good tacklers foul less


def test_red_card_lowers_the_lines_the_player_fed() -> None:
    xi = _xi()
    full = _rate(xi)
    without_cb = _rate([sp for sp in xi if sp[1].id != "p02"])
    assert without_cb.defence < full.defence
    assert without_cb.attack < full.attack  # defenders contribute a little to attack
    without_st = _rate([sp for sp in xi if sp[1].id != "p09"])
    assert full.attack - without_st.attack > full.attack - without_cb.attack


def test_outfield_player_in_goal_gives_low_goalkeeping() -> None:
    xi = _xi()
    keeper = player("px", positions={Position.ST: 20}, attributes=attrs(10))
    stand_in = [(Position.GK, keeper), *xi[1:]]
    assert _rate(stand_in).goalkeeping < _rate(xi).goalkeeping / 2
    assert _rate(xi[1:]).goalkeeping == 1.0  # no one in goal


def test_independent_of_player_order() -> None:
    xi = _xi(s9={"finishing": 17}, s3={"marking": 4})
    shuffled = list(xi)
    random.Random(3).shuffle(shuffled)
    assert _rate(xi) == _rate(shuffled)
