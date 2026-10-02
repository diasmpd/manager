"""FMF-style seeded draw (research R5)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.draw import draw_groups
from manager_core.competition.rules import DrawMethod, GroupStageRule, Matching, load_ruleset
from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset


@pytest.fixture(scope="module")
def world() -> Dataset:
    dataset = api.load_dataset(Path(__file__).resolve().parents[3] / "data" / "sample").dataset
    assert dataset is not None
    return dataset


def _clubs(world: Dataset) -> list[Club]:
    return list(world.clubs.values())


def test_strongest_clubs_head_groups(world: Dataset) -> None:
    rule = load_ruleset("mg-modulo-i-2026").group_stage
    groups = draw_groups(_clubs(world), rule, seed=1)
    assert [g.label for g in groups] == ["A", "B", "C"]
    heads = {g.club_ids[0] for g in groups}
    assert heads == {"vale-do-ouro", "serra-negra", "alvorada"}


def test_one_club_per_pot_per_group(world: Dataset) -> None:
    rule = load_ruleset("mg-modulo-i-2026").group_stage
    ranked = sorted(_clubs(world), key=lambda c: (-c.reputation, c.id))
    pots = [{c.id for c in ranked[i * 3:(i + 1) * 3]} for i in range(4)]
    for seed in range(50):
        for g in draw_groups(_clubs(world), rule, seed):
            assert len(g.club_ids) == 4
            for pot_index, club_id in enumerate(g.club_ids):
                assert club_id in pots[pot_index]


def test_deterministic_and_seed_sensitive(world: Dataset) -> None:
    rule = load_ruleset("mg-modulo-i-2026").group_stage
    assert draw_groups(_clubs(world), rule, 7) == draw_groups(_clubs(world), rule, 7)
    draws = {tuple(g.club_ids for g in draw_groups(_clubs(world), rule, s)) for s in range(20)}
    assert len(draws) > 1


def test_input_order_does_not_matter(world: Dataset) -> None:
    rule = load_ruleset("mg-modulo-i-2026").group_stage
    clubs = _clubs(world)
    assert draw_groups(clubs, rule, 3) == draw_groups(list(reversed(clubs)), rule, 3)


def test_fixed_draw(world: Dataset) -> None:
    ids = sorted(world.clubs)
    fixed = (tuple(ids[0:4]), tuple(ids[4:8]), tuple(ids[8:12]))
    rule = GroupStageRule("x", 3, 4, Matching.OTHER_GROUPS, 1, DrawMethod.FIXED, fixed)
    groups = draw_groups(_clubs(world), rule, seed=99)
    assert tuple(g.club_ids for g in groups) == fixed
