"""Group-stage fixture generation (research R6)."""

from collections import Counter

import pytest

from manager_core.competition.draw import Group
from manager_core.competition.fixtures import build_group_fixtures
from manager_core.competition.rules import Matching

GROUPS = (
    Group("A", ("a1", "a2", "a3", "a4")),
    Group("B", ("b1", "b2", "b3", "b4")),
    Group("C", ("c1", "c2", "c3", "c4")),
)
ALL_CLUBS = [c for g in GROUPS for c in g.club_ids]


@pytest.mark.parametrize("seed", range(200))
def test_other_groups_invariants(seed: int) -> None:
    matchdays = build_group_fixtures(GROUPS, Matching.OTHER_GROUPS, rounds=1, seed=seed)
    assert len(matchdays) == 8
    group_of = {c: g.label for g in GROUPS for c in g.club_ids}
    opponents: dict[str, set[str]] = {c: set() for c in ALL_CLUBS}
    home = Counter[str]()
    for day in matchdays:
        assert len(day) == 6
        playing = [c for pair in day for c in pair]
        assert sorted(playing) == sorted(ALL_CLUBS)  # everyone exactly once per matchday
        for h, a in day:
            assert group_of[h] != group_of[a]
            opponents[h].add(a)
            opponents[a].add(h)
            home[h] += 1
    for club in ALL_CLUBS:
        assert opponents[club] == {c for c in ALL_CLUBS if group_of[c] != group_of[club]}
        assert home[club] == 4


def test_deterministic() -> None:
    a = build_group_fixtures(GROUPS, Matching.OTHER_GROUPS, 1, seed=5)
    b = build_group_fixtures(GROUPS, Matching.OTHER_GROUPS, 1, seed=5)
    assert a == b


def test_double_round_robin_all() -> None:
    group = (Group("A", tuple(f"t{i}" for i in range(8))),)
    matchdays = build_group_fixtures(group, Matching.ALL, rounds=2, seed=1)
    assert len(matchdays) == 14
    pairs = Counter((h, a) for day in matchdays for h, a in day)
    clubs = group[0].club_ids
    for x in clubs:
        for y in clubs:
            if x != y:
                assert pairs[(x, y)] == 1  # each pair once at each home
    for day in matchdays:
        assert sorted(c for pair in day for c in pair) == sorted(clubs)


def test_own_group_round_robin() -> None:
    matchdays = build_group_fixtures(GROUPS, Matching.OWN_GROUP, rounds=1, seed=2)
    assert len(matchdays) == 3
    for day in matchdays:
        for h, a in day:
            assert h[0] == a[0]  # same group letter
