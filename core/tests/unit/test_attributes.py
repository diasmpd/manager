import pytest

from manager_core.domain.attributes import (
    ALL_ATTRIBUTES,
    ATTRIBUTE_GROUPS,
    HIDDEN_DEFAULTS,
    AttributeGroup,
    Attributes,
    visible_for,
)

FM_TECHNICAL = (
    "corners", "crossing", "dribbling", "finishing", "first_touch", "free_kick_taking", "heading",
    "long_shots", "long_throws", "marking", "passing", "penalty_taking", "tackling", "technique",
)


def make(**overrides: int) -> Attributes:
    values = dict.fromkeys(ALL_ATTRIBUTES, 10)
    values.update(overrides)
    return Attributes(**values)


def test_group_sizes_match_fm() -> None:
    sizes = {group: len(names) for group, names in ATTRIBUTE_GROUPS.items()}
    assert sizes == {
        AttributeGroup.TECHNICAL: 14,
        AttributeGroup.MENTAL: 14,
        AttributeGroup.PHYSICAL: 8,
        AttributeGroup.GOALKEEPING: 11,
        AttributeGroup.HIDDEN: 13,
    }
    assert len(ALL_ATTRIBUTES) == 60
    assert len(set(ALL_ATTRIBUTES)) == 60


def test_fm_order_is_kept() -> None:
    assert ATTRIBUTE_GROUPS[AttributeGroup.TECHNICAL] == FM_TECHNICAL
    assert ALL_ATTRIBUTES[:14] == FM_TECHNICAL


@pytest.mark.parametrize("bad", [0, 21, -3])
def test_range_is_enforced(bad: int) -> None:
    with pytest.raises(ValueError):
        make(finishing=bad)


def test_bounds_are_inclusive() -> None:
    assert make(finishing=1, pace=20).pace == 20


def test_hidden_defaults() -> None:
    expected = dict.fromkeys(ATTRIBUTE_GROUPS[AttributeGroup.HIDDEN], 10)
    expected.update(dirtiness=8, injury_proneness=8, controversy=6)
    assert expected == HIDDEN_DEFAULTS


def test_attributes_are_immutable() -> None:
    attrs = make()
    with pytest.raises(AttributeError):
        attrs.finishing = 15  # type: ignore[misc]


def test_display_groups_outfield() -> None:
    groups = visible_for(is_goalkeeper=False)
    assert list(groups) == [AttributeGroup.TECHNICAL, AttributeGroup.MENTAL, AttributeGroup.PHYSICAL]
    assert groups[AttributeGroup.TECHNICAL] == FM_TECHNICAL


def test_display_groups_goalkeeper() -> None:
    groups = visible_for(is_goalkeeper=True)
    assert list(groups) == [
        AttributeGroup.GOALKEEPING, AttributeGroup.MENTAL, AttributeGroup.PHYSICAL,
        AttributeGroup.TECHNICAL,
    ]
    assert groups[AttributeGroup.TECHNICAL] == (
        "first_touch", "free_kick_taking", "passing", "penalty_taking", "technique",
    )
    assert AttributeGroup.HIDDEN not in groups
