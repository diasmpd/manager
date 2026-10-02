"""US2: best XI is the exact optimum, deterministic on ties, and fast (SC-006, research R9)."""

import itertools
import random
import time
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.formation import load_catalogue
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.ratings.lineup import best_assignment, best_xi, rank_for_position
from manager_core.ratings.suitability import suitability_milli
from tests.helpers import attrs, player


def _random_player(rng: random.Random, pid: str) -> Player:
    main = rng.choice(list(Position))
    positions = {main: 20, rng.choice(list(Position)): rng.randint(1, 17)}
    positions[main] = 20
    return player(pid, positions=positions, attributes=attrs(rng.randint(5, 16),
                  finishing=rng.randint(1, 20), tackling=rng.randint(1, 20),
                  passing=rng.randint(1, 20), reflexes=rng.randint(1, 20),
                  pace=rng.randint(1, 20)))


def _brute_force(players: list[Player], slots: list[Position]) -> int:
    best = -1
    for chosen in itertools.permutations(players, len(slots)):
        total = sum(suitability_milli(p, s) for p, s in zip(chosen, slots, strict=True))
        best = max(best, total)
    return best


@pytest.mark.parametrize("seed", range(20))
def test_matches_brute_force(seed: int) -> None:
    rng = random.Random(seed)
    slots = [Position.GK, *rng.sample(list(Position)[1:], 4)]
    players = [_random_player(rng, f"p-{i:02d}") for i in range(rng.randint(6, 8))]
    result = best_assignment(players, slots)
    assert result.total_milli == _brute_force(players, slots)
    assert len({a.player_id for a in result.assignments}) == len(slots)


def test_totals_are_integers() -> None:
    rng = random.Random(1)
    players = [_random_player(rng, f"p-{i:02d}") for i in range(14)]
    lineup = best_xi(players, load_catalogue()["4-4-2"])
    assert isinstance(lineup.total_milli, int)
    assert all(isinstance(a.suitability_milli, int) for a in lineup.assignments)


def test_one_player_per_slot_and_one_goalkeeper(sample_dir: Path) -> None:
    dataset = api.load_dataset(sample_dir).dataset
    assert dataset is not None
    squad = list(dataset.squad("vale-do-ouro"))
    for formation in load_catalogue().values():
        lineup = best_xi(squad, formation)
        ids = [a.player_id for a in lineup.assignments]
        assert len(ids) == 11 and len(set(ids)) == 11
        gk = [a for a in lineup.assignments if a.position is Position.GK]
        assert len(gk) == 1
        assert "outfield_in_goal" not in lineup.flags


def _tied_squad() -> list[Player]:
    """Identical players: every lineup using them has exactly the same integer total."""
    same = attrs(12)
    players = [player(f"p-gk{i}", positions={Position.GK: 20}, attributes=same) for i in (2, 1)]
    everywhere = dict.fromkeys(
        (Position.MC, Position.DC, Position.ST, Position.ML, Position.MR, Position.DL, Position.DR),
        20,
    )
    shuffled_ids = (13, 4, 11, 1, 7, 2, 9, 12, 5, 3, 8, 10, 6)
    players += [player(f"p-x{i:02d}", positions=everywhere, attributes=same) for i in shuffled_ids]
    return players


def test_ties_resolve_to_smallest_ids_in_slot_order() -> None:
    formation = load_catalogue()["4-4-2"]
    lineup = best_xi(_tied_squad(), formation)
    ids = [a.player_id for a in lineup.assignments]
    assert ids[0] == "p-gk1"
    assert ids[1:] == [f"p-x{i:02d}" for i in range(1, 11)]


def test_ties_are_stable_across_runs_and_input_orders() -> None:
    formation = load_catalogue()["4-4-2"]
    expected = best_xi(_tied_squad(), formation)
    rng = random.Random(42)
    for _ in range(100):
        shuffled = _tied_squad()
        rng.shuffle(shuffled)
        assert best_xi(shuffled, formation) == expected


def test_no_fit_goalkeeper_is_flagged() -> None:
    players = [player(f"p-{i:02d}", positions={Position.MC: 20}) for i in range(12)]
    lineup = best_xi(players, load_catalogue()["4-4-2"])
    assert len(lineup.assignments) == 11
    assert "outfield_in_goal" in lineup.flags


def test_rank_for_position_orders_by_suitability_then_id() -> None:
    natural = player("p-b", positions={Position.DC: 20})
    twin = player("p-a", positions={Position.DC: 20})
    unfamiliar = player("p-c", positions={Position.ST: 20, Position.DC: 9})
    ranking = rank_for_position([unfamiliar, natural, twin], Position.DC)
    assert [p.id for p, _ in ranking] == ["p-a", "p-b", "p-c"]


def test_full_squad_is_fast(sample_dir: Path) -> None:
    dataset = api.load_dataset(sample_dir).dataset
    assert dataset is not None
    squad = list(dataset.squad("vale-do-ouro"))
    timings = []
    for _ in range(3):  # best of 3: robust to a busy machine (e.g. a parallel test run)
        start = time.perf_counter()
        best_xi(squad, load_catalogue()["4-3-3"])
        timings.append(time.perf_counter() - start)
    assert min(timings) < 0.5
