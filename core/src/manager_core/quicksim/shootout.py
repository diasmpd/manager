"""Player-based penalty shootouts (FR-013, research R11; IFAB Law 10).

Only the players on the pitch at the final whistle take part. If one team has more players, it
reduces to the opponents' number before the kicks (IFAB Law 10), leaving out its worst takers
and keeping its goalkeeper. Each side kicks in order of
penalty-taking ability; the order restarts after every eligible player has kicked. Each kick is
scored with a probability that depends on the taker and on the opposing goalkeeper.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from manager_core.competition.results import SHOOTOUT_ROUNDS, Shootout
from manager_core.domain.player import Player
from manager_core.quicksim.engine import kick_factor, penalty_order
from manager_core.quicksim.params import ModelParams


def play_shootout(first_id: str, first: Sequence[Player], first_keeper: Player | None,
                  second_id: str, second: Sequence[Player], second_keeper: Player | None,
                  params: ModelParams, rng: random.Random) -> Shootout:
    """`first` kicks first. Kicks alternate; 5 each, then sudden death."""
    first_order, second_order = shootout_orders(first, first_keeper, second, second_keeper)
    orders = {first_id: first_order, second_id: second_order}
    keepers = {first_id: second_keeper, second_id: first_keeper}  # the keeper each side faces
    kicks: list[tuple[str, bool]] = []
    goals = {first_id: 0, second_id: 0}
    taken = {first_id: 0, second_id: 0}
    while True:
        for club in (first_id, second_id):
            order = orders[club]
            taker = order[taken[club] % len(order)]
            scored = rng.random() < kick_factor(params, taker, keepers[club])
            kicks.append((club, scored))
            taken[club] += 1
            goals[club] += int(scored)
            if _decided(goals, taken, first_id, second_id):
                winner = max(goals, key=lambda c: goals[c])
                return Shootout(tuple(kicks), winner)


def _decided(goals: dict[str, int], taken: dict[str, int], first: str, second: str) -> bool:
    if taken[first] <= SHOOTOUT_ROUNDS and taken[second] <= SHOOTOUT_ROUNDS:
        return (goals[first] > goals[second] + SHOOTOUT_ROUNDS - taken[second]
                or goals[second] > goals[first] + SHOOTOUT_ROUNDS - taken[first])
    return taken[first] == taken[second] and goals[first] != goals[second]


def kicking_order(players: Sequence[Player], keeper: Player | None) -> list[Player]:
    """Outfield players by penalty ability, then the goalkeeper last."""
    outfield = [p for p in players if keeper is None or p.id != keeper.id]
    return penalty_order(outfield) + ([keeper] if keeper is not None and keeper in players
                                      else [])


def shootout_orders(first: Sequence[Player], first_keeper: Player | None,
                    second: Sequence[Player], second_keeper: Player | None,
                    ) -> tuple[list[Player], list[Player]]:
    """Both kicking orders after reducing the larger side to the smaller one's number
    (IFAB Law 10): it drops its worst takers, never its goalkeeper."""
    first_order = kicking_order(first, first_keeper)
    second_order = kicking_order(second, second_keeper)
    size = min(len(first_order), len(second_order))
    return _reduce(first_order, first_keeper, size), _reduce(second_order, second_keeper, size)


def _reduce(order: list[Player], keeper: Player | None, size: int) -> list[Player]:
    if len(order) <= size:
        return order
    kept_keeper = [keeper] if keeper is not None and keeper in order else []
    outfield = [p for p in order if p not in kept_keeper]  # already best takers first
    return outfield[: size - len(kept_keeper)] + kept_keeper


def kick_takers(shootout: Shootout, first: Sequence[Player], first_keeper: Player | None,
                second: Sequence[Player], second_keeper: Player | None) -> list[str]:
    """The taker of each kick, derived from the finishers (the order is deterministic)."""
    first_id, second_id = shootout.kicks[0][0], shootout.kicks[1][0]
    first_order, second_order = shootout_orders(first, first_keeper, second, second_keeper)
    orders = {first_id: first_order, second_id: second_order}
    taken = {first_id: 0, second_id: 0}
    takers = []
    for club, _ in shootout.kicks:
        order = orders[club]
        takers.append(order[taken[club] % len(order)].id)
        taken[club] += 1
    return takers
