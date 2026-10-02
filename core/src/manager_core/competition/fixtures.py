"""Group-stage fixtures (research R6).

`other_groups`: every matchday is a perfect matching of the cross-group graph, found by a
seeded backtracking search over all matchdays at once; home/away comes from an Eulerian
orientation, which gives every club exactly half its matches at home.
`all` / `own_group`: round-robin by the circle method; a second round mirrors the first.
"""

from __future__ import annotations

import random
from collections.abc import Iterator, Sequence

from manager_core.competition.draw import Group
from manager_core.competition.rules import Matching

Pair = tuple[str, str]  # (home, away)
Matchday = list[Pair]


def build_group_fixtures(groups: Sequence[Group], matching: Matching, rounds: int,
                         seed: int) -> list[Matchday]:
    if matching is Matching.OTHER_GROUPS:
        first = _other_groups(groups, seed)
    elif matching is Matching.ALL:
        first = _round_robin([c for g in groups for c in g.club_ids])
    else:
        per_group = [_round_robin(list(g.club_ids)) for g in groups]
        first = [[p for day in days for p in day] for days in zip(*per_group, strict=True)]
    if rounds == 2:
        return first + [[(a, h) for h, a in day] for day in first]
    return first


# ---- other_groups ---------------------------------------------------------------------------


def _other_groups(groups: Sequence[Group], seed: int) -> list[Matchday]:
    group_of = {c: g.label for g in groups for c in g.club_ids}
    clubs = sorted(group_of)
    rng = random.Random(seed)
    remaining = {c: [o for o in clubs if group_of[o] != group_of[c]] for c in clubs}
    for options in remaining.values():
        rng.shuffle(options)
    degree = len(next(iter(remaining.values())))
    days: list[list[tuple[str, str]]] = []
    if not _search(clubs, remaining, days, degree):
        raise ValueError("no valid matchday schedule exists for these groups")
    edges = [pair for day in days for pair in day]
    home_of = _orient(clubs, edges)
    return [[(a, b) if home_of[frozenset((a, b))] == a else (b, a) for a, b in day]
            for day in days]


def _search(clubs: list[str], remaining: dict[str, list[str]], days: list[list[tuple[str, str]]],
            total_days: int) -> bool:
    if len(days) == total_days:
        return True
    for matching in _matchings(clubs, remaining, [], set()):
        for a, b in matching:
            remaining[a].remove(b)
            remaining[b].remove(a)
        days.append(matching)
        if _search(clubs, remaining, days, total_days):
            return True
        days.pop()
        for a, b in matching:
            remaining[a].append(b)
            remaining[b].append(a)
    return False


def _matchings(clubs: list[str], remaining: dict[str, list[str]], current: list[tuple[str, str]],
               used: set[str]) -> Iterator[list[tuple[str, str]]]:
    free = next((c for c in clubs if c not in used), None)
    if free is None:
        yield list(current)
        return
    for opponent in list(remaining[free]):
        if opponent in used:
            continue
        used.update((free, opponent))
        current.append((free, opponent))
        yield from _matchings(clubs, remaining, current, used)
        current.pop()
        used.difference_update((free, opponent))


def _orient(clubs: list[str], edges: list[tuple[str, str]]) -> dict[frozenset[str], str]:
    """Eulerian orientation (every degree is even): in-degree == out-degree for every club."""
    adjacency: dict[str, list[str]] = {c: [] for c in clubs}
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    for c in clubs:
        adjacency[c].sort(reverse=True)
    used: set[frozenset[str]] = set()
    home_of: dict[frozenset[str], str] = {}
    for start in clubs:
        stack = [start]
        while stack:
            node = stack[-1]
            while adjacency[node] and frozenset((node, adjacency[node][-1])) in used:
                adjacency[node].pop()
            if not adjacency[node]:
                stack.pop()
                continue
            nxt = adjacency[node].pop()
            key = frozenset((node, nxt))
            used.add(key)
            home_of[key] = node  # walking node -> nxt: node hosts
            stack.append(nxt)
    return home_of


# ---- round robin ----------------------------------------------------------------------------


def _round_robin(clubs: list[str]) -> list[Matchday]:
    if len(clubs) % 2:
        raise ValueError("round-robin needs an even number of clubs")
    order = sorted(clubs)
    n = len(order)
    fixed, rotating = order[0], order[1:]
    days: list[Matchday] = []
    for r in range(n - 1):
        ring = [fixed, *rotating]
        day: Matchday = []
        for i in range(n // 2):
            a, b = ring[i], ring[n - 1 - i]
            day.append((a, b) if (r + i) % 2 == 0 else (b, a))
        days.append(day)
        rotating = rotating[-1:] + rotating[:-1]
    return days
