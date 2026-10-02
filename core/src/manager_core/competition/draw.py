"""Group draw (research R5): FMF-style seeded pots."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from string import ascii_uppercase

from manager_core.competition.rules import DrawMethod, GroupStageRule
from manager_core.domain.club import Club


@dataclass(frozen=True, slots=True)
class Group:
    label: str
    club_ids: tuple[str, ...]  # in draw order: pot 1 first


def draw_groups(clubs: Sequence[Club], rule: GroupStageRule, seed: int) -> tuple[Group, ...]:
    labels = ascii_uppercase[: rule.group_count]
    if rule.draw is DrawMethod.FIXED:
        pairs = zip(labels, rule.fixed_groups, strict=True)
        return tuple(Group(label, ids) for label, ids in pairs)
    # Pots by reputation (M0 stand-in for the FMF ranking); ties broken by id.
    ranked = sorted(clubs, key=lambda c: (-c.reputation, c.id))
    rng = random.Random(seed)
    members: list[list[str]] = [[] for _ in labels]
    k = rule.group_count
    for pot_index in range(rule.group_size):
        pot = [c.id for c in ranked[pot_index * k:(pot_index + 1) * k]]
        rng.shuffle(pot)
        for group, club_id in zip(members, pot, strict=True):
            group.append(club_id)
    return tuple(Group(label, tuple(ids)) for label, ids in zip(labels, members, strict=True))
