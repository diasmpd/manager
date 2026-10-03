"""Regression: the keeper at the final whistle after a goalkeeper is sent off.

`keeper_at_end` used to guess the keeper as "the last substitute still on the pitch", which was
wrong when another substitution followed the reserve keeper, or when an outfield player went in
goal. The report now records the keeper the engine had in the GK slot.
"""

import dataclasses
import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import _Match, goalkeeper_on
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.ratings import POSITION_GROUP, Group
from manager_core.quicksim.report import HOME, Minute, check_invariants, keeper_at_end
from manager_core.quicksim.shootout import kicking_order
from manager_core.quicksim.squad import TeamSheet

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> tuple[Dataset, QuickSimProvider]:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset, QuickSimProvider(loaded.dataset)


def _starting_keeper(sheet: TeamSheet) -> str:
    return next(pid for i, pid in sheet.starters if sheet.slot_position(i) is Position.GK)


def _is_keeper(dataset: Dataset, pid: str) -> bool:
    player = dataset.player(pid)
    best = max(player.positions.natural_positions(),
               key=lambda pos: (player.positions[pos], -pos.order))
    return POSITION_GROUP[best] is Group.GOALKEEPER


def _match(world: tuple[Dataset, QuickSimProvider], home: TeamSheet) -> _Match:
    dataset, provider = world
    return _Match(home, provider.team_sheet("serra-negra"), dataset.players, provider.params,
                  random.Random(1), neutral=False)


def test_reserve_keeper_stays_the_keeper_after_a_later_sub(
        world: tuple[Dataset, QuickSimProvider]) -> None:
    dataset, provider = world
    sheet = provider.team_sheet("vale-do-ouro")
    reserve = next(b for b in sheet.bench if _is_keeper(dataset, b))
    match = _match(world, sheet)
    match._send_off(HOME, Minute(30), _starting_keeper(sheet), "red")
    assert reserve in match.sides[HOME].on.values()
    match._substitute(HOME, Minute(70), 1)  # a normal outfield substitution afterwards
    later = [e for e in match.events if e.kind == "sub" and e.minute == Minute(70)]
    assert later and later[-1].other_player_id != reserve
    report = match.report((2, 5))
    assert check_invariants(report) == []
    assert report.keeper(HOME) == reserve
    assert keeper_at_end(report, HOME) == reserve
    finishers = [dataset.player(p) for p in sorted(report.home_finishers)]
    assert kicking_order(finishers, dataset.player(reserve))[-1].id == reserve  # kicks last


def test_outfield_player_in_goal_is_the_keeper(
        world: tuple[Dataset, QuickSimProvider]) -> None:
    dataset, provider = world
    full = provider.team_sheet("vale-do-ouro")
    sheet = dataclasses.replace(
        full, bench=tuple(b for b in full.bench if not _is_keeper(dataset, b)))
    match = _match(world, sheet)
    match._send_off(HOME, Minute(30), _starting_keeper(sheet), "red")
    stand_in = goalkeeper_on(match.sides[HOME])
    assert stand_in is not None and not _is_keeper(dataset, stand_in.id)
    match._substitute(HOME, Minute(70), 1)
    report = match.report((2, 5))
    assert check_invariants(report) == []
    assert report.keeper(HOME) == stand_in.id
    assert keeper_at_end(report, HOME) == stand_in.id


def test_recorded_keeper_must_be_a_finisher(world: tuple[Dataset, QuickSimProvider]) -> None:
    _, provider = world
    match = _match(world, provider.team_sheet("vale-do-ouro"))
    report = match.report((2, 5))
    assert report.keeper(HOME) == _starting_keeper(provider.team_sheet("vale-do-ouro"))
    broken = dataclasses.replace(report, home_keeper="nobody")
    assert "keeper_not_on_pitch:home" in check_invariants(broken)
