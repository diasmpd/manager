import pytest

pytest.importorskip("hypothesis")  # dev dependency; skip cleanly in a bare interpreter

from hypothesis import given, settings
from hypothesis import strategies as st

from manager_core.domain.attributes import (
    ALL_ATTRIBUTES,
    ATTRIBUTE_GROUPS,
    AttributeGroup,
    Attributes,
)
from manager_core.domain.positions import Position
from manager_core.ratings.ability import best_position, current_ability, is_goalkeeper
from tests.helpers import attrs, player

VISIBLE = [n for n in ALL_ATTRIBUTES if n not in ATTRIBUTE_GROUPS[AttributeGroup.HIDDEN]]


def test_all_tens_gives_95() -> None:
    # S = 10 -> CA = round(1 + 9 * 199 / 19) = 95
    assert current_ability(player(positions={Position.DC: 20})) == 95


def test_extremes_clamp() -> None:
    assert current_ability(player(attributes=attrs(20))) == 200
    assert current_ability(player(attributes=attrs(1))) == 1


def test_hidden_attributes_do_not_count() -> None:
    low = player(attributes=attrs(10, consistency=1, temperament=1))
    high = player(attributes=attrs(10, consistency=20, temperament=20))
    assert current_ability(low) == current_ability(high)


def test_best_position_ignores_unfamiliar_positions() -> None:
    # Great striker attributes, but he is only natural at DC: best position must be DC.
    p = player(positions={Position.DC: 20, Position.ST: 12}, attributes=attrs(8, finishing=20))
    assert best_position(p) is Position.DC


def test_best_position_tie_uses_fm_order() -> None:
    p = player(positions={Position.MR: 20, Position.ML: 20})
    assert best_position(p) is Position.ML


def test_is_goalkeeper() -> None:
    assert is_goalkeeper(player(positions={Position.GK: 20}))
    assert not is_goalkeeper(player(positions={Position.ST: 20}))


positions_strategy = st.dictionaries(
    st.sampled_from(list(Position)), st.integers(1, 20), min_size=1, max_size=5
).filter(lambda d: any(v >= 15 for v in d.values()))


@settings(max_examples=300, deadline=None)
@given(
    values=st.lists(st.integers(1, 20), min_size=60, max_size=60),
    positions=positions_strategy,
    bumped=st.sampled_from(VISIBLE),
)
def test_ca_is_monotonic(values: list[int], positions: dict[Position, int], bumped: str) -> None:
    base = dict(zip(ALL_ATTRIBUTES, values, strict=True))
    before = current_ability(player(positions=positions, attributes=Attributes(**base)))
    if base[bumped] < 20:
        base[bumped] += 1
    after = current_ability(player(positions=positions, attributes=Attributes(**base)))
    assert after >= before
