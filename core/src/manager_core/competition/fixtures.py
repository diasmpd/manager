"""Group-stage fixtures (research R6).

`other_groups`: every matchday is a perfect matching of the cross-group graph, found by a
seeded backtracking search over all matchdays at once; home/away is then chosen so every club
has exactly half its matches at home and never more than 2 home or 2 away in a row.
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
    home_of = _orient(days, clubs)
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


MAX_STREAK = 2  # no club plays more than 2 home or 2 away matches in a row (owner decision)


def _orient(days: list[list[tuple[str, str]]], clubs: list[str]) -> dict[frozenset[str], str]:
    """Choose the host of every match: exactly half of each club's matches at home and never
    more than MAX_STREAK home or away matches in a row. Exact backtracking in matchday order."""
    pairs = [pair for day in days for pair in day]
    total = {c: 0 for c in clubs}
    for a, b in pairs:
        total[a] += 1
        total[b] += 1
    homes = {c: 0 for c in clubs}
    played = {c: 0 for c in clubs}
    streak: dict[str, tuple[str, int]] = {c: ("", 0) for c in clubs}
    choice: dict[frozenset[str], str] = {}

    def fits(club: str, venue: str) -> bool:
        target = total[club] // 2
        home_after = homes[club] + (venue == "H")
        away_after = played[club] + 1 - home_after
        if home_after > target or away_after > total[club] - target:
            return False
        last, length = streak[club]
        return not (last == venue and length >= MAX_STREAK)

    def apply(club: str, venue: str) -> tuple[str, int]:
        before = streak[club]
        homes[club] += venue == "H"
        played[club] += 1
        streak[club] = (venue, before[1] + 1 if before[0] == venue else 1)
        return before

    def undo(club: str, venue: str, before: tuple[str, int]) -> None:
        homes[club] -= venue == "H"
        played[club] -= 1
        streak[club] = before

    def search(index: int) -> bool:
        if index == len(pairs):
            return True
        a, b = pairs[index]
        # try the club that needs home matches more first (deterministic)
        options = [(a, b), (b, a)]
        options.sort(key=lambda o: (homes[o[0]] - played[o[0]] / 2, o[0]))
        for host, guest in options:
            if fits(host, "H") and fits(guest, "A"):
                saved_host, saved_guest = apply(host, "H"), apply(guest, "A")
                choice[frozenset((a, b))] = host
                if search(index + 1):
                    return True
                undo(host, "H", saved_host)
                undo(guest, "A", saved_guest)
        return False

    if not search(0):
        raise ValueError("no home/away assignment satisfies the balance and streak rules")
    return choice


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
