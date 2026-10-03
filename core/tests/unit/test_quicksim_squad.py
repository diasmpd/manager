"""Team sheets: XI from 001's best XI, bench, cache (research R7, R12)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.squad import (
    BENCH_SIZE,
    NO_GOALKEEPER,
    SHORT_SQUAD,
    build_team_sheet,
)
from manager_core.ratings.ability import is_goalkeeper
from tests.helpers import attrs, player

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def test_xi_is_the_best_xi_and_bench_has_a_keeper(world: Dataset) -> None:
    club = "vale-do-ouro"
    sheet = build_team_sheet(club, sorted(world.squad(club), key=lambda p: p.id))
    best = api.suggest_lineup(world, club, "4-4-2")
    assert sorted(sheet.starters) == sorted((a.slot_index, a.player_id) for a in best.assignments)
    assert len(sheet.bench) == BENCH_SIZE
    assert not set(sheet.bench) & {pid for _, pid in sheet.starters}
    assert is_goalkeeper(world.player(sheet.bench[0]))
    assert sheet.flags == ()


def test_sheets_are_cached_per_dataset(world: Dataset) -> None:
    a = QuickSimProvider(world)
    sheet = a.team_sheet("alvorada")
    b = QuickSimProvider(world)
    assert b.team_sheet("alvorada") is sheet


def test_short_squad_without_keeper_still_fields_a_side() -> None:
    squad = [player(f"o{i:02d}", positions={Position.MC: 20}, attributes=attrs(10))
             for i in range(10)]
    sheet = build_team_sheet("tiny", squad)
    assert len(sheet.starters) == 10
    assert any(sheet.slot_position(i) is Position.GK for i, _ in sheet.starters)
    assert SHORT_SQUAD in sheet.flags and NO_GOALKEEPER in sheet.flags
    assert sheet.bench == ()
