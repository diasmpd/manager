"""The user's team selection (spec 005 FR-003/FR-004, research R2)."""

import dataclasses
import random
import sqlite3
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import Career
from manager_core.career.selection import Selection, propose, to_team_sheet, validate
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


@pytest.fixture
def career(world: Dataset) -> Career:
    return api.new_career(world, "sel", "alvorada", master_seed=1)


def _codes(career: Career, selection: Selection) -> list[str]:
    return [i.code for i in validate(career, selection)]


def test_proposal_is_the_assistants_xi(career: Career) -> None:
    sel = propose(career, "4-3-3")
    assert sel.formation == "4-3-3" and len(sel.starters) == 11 and len(sel.bench) == 9
    assert _codes(career, sel) == []
    best = api.suggest_lineup(career.world, "alvorada", "4-3-3")
    assert sorted(sel.starters) == sorted((a.slot_index, a.player_id) for a in best.assignments)


def test_errors(career: Career) -> None:
    sel = propose(career, "4-4-2")
    starters = list(sel.starters)
    outsider = next(m.player_id for m in career.world.memberships.values()
                    if m.club_id != "alvorada")
    starters[3] = (starters[3][0], outsider)
    assert "not_in_squad" in _codes(career, dataclasses.replace(sel, starters=tuple(starters)))
    starters = list(sel.starters)
    starters[3] = (starters[3][0], starters[4][1])
    assert "duplicate" in _codes(career, dataclasses.replace(sel, starters=tuple(starters)))
    long_bench = (*sel.bench, sel.bench[0])
    assert "bench_too_long" in _codes(career, dataclasses.replace(sel, bench=long_bench))
    assert "unknown_formation" in _codes(career, dataclasses.replace(sel, formation="1-1-8"))


def test_no_goalkeeper_is_only_a_warning(career: Career) -> None:
    sel = propose(career, "4-4-2")
    sheet = to_team_sheet(career, sel)
    gk_slot = next(i for i, _ in sel.starters if sheet.slot_position(i) is Position.GK)
    outfielder = next(pid for i, pid in sel.starters if i != gk_slot)
    swapped = tuple((i, outfielder if i == gk_slot else
                     (dict(sel.starters)[gk_slot] if pid == outfielder else pid))
                    for i, pid in sel.starters)
    issues = validate(career, dataclasses.replace(sel, starters=swapped))
    assert [(i.code, i.severity) for i in issues] == [("no_goalkeeper", "warning")]


def test_suspended_player_is_refused(career: Career) -> None:
    sel = propose(career, "4-4-2")
    star = sel.starters[-1][1]
    ledger = career.season.discipline
    ledger._bans[star] = 1  # type: ignore[union-attr]
    issues = validate(career, sel)
    assert ("suspended", star) in [(i.code, i.player_id) for i in issues]
    fresh = propose(career, "4-4-2")
    assert star not in {pid for _, pid in fresh.starters} | set(fresh.bench)


@pytest.mark.parametrize("seed", range(60))
def test_a_suspended_player_never_validates(world: Dataset, seed: int) -> None:
    """SC-004: any selection containing a suspended player has an error (60 random cases)."""
    rnd = random.Random(seed)
    career = api.new_career(world, "prop", "alvorada", master_seed=2)
    squad = sorted(m.player_id for m in world.memberships.values() if m.club_id == "alvorada")
    suspended = rnd.choice(squad)
    career.season.discipline._bans[suspended] = 1  # type: ignore[union-attr]
    picked = rnd.sample(squad, 20)
    if suspended not in picked:
        picked[rnd.randrange(20)] = suspended
    sel = Selection("4-4-2", tuple(enumerate(picked[:11])), tuple(picked[11:]))
    assert any(i.code == "suspended" and i.severity == "error" for i in validate(career, sel))


def test_confirmed_selection_is_played(career: Career, tmp_path: Path) -> None:
    """SC-002: the report's lineup equals the confirmed selection."""
    sel = propose(career, "4-3-3")
    bench_player = sel.bench[2]
    starters = list(sel.starters)
    starters[5] = (starters[5][0], bench_player)
    out = sel.starters[5][1]
    bench = tuple(out if pid == bench_player else pid for pid in sel.bench)
    chosen = Selection("4-3-3", tuple(starters), bench)
    stop = api.continue_career(career, tmp_path)
    while stop.kind != "user_match":
        stop = api.continue_career(career, tmp_path)
    api.confirm_selection(career, chosen)
    api.continue_career(career, tmp_path)
    report = career.season.results[stop.match_id or ""].report
    assert report is not None
    side = "home" if career.season.matches[stop.match_id or ""].home_id == "alvorada" else "away"
    lineup = report.lineup(side)
    assert lineup.formation == "4-3-3"
    assert sorted(pid for _, pid in lineup.starters) == sorted(pid for _, pid in starters)
    assert lineup.bench == bench


def test_selection_survives_save_load_and_migration(career: Career, tmp_path: Path) -> None:
    chosen = propose(career, "4-3-3")
    api.confirm_selection(career, chosen)
    api.save_career(career, tmp_path)
    loaded = api.load_career(tmp_path, "sel")
    assert loaded.selection == chosen
    assert loaded.live_provider.team_sheet("alvorada").formation.name == "4-3-3"
    # a format-1 save (004) has no selection table: it is migrated and loads without one
    with sqlite3.connect(tmp_path / "sel.sqlite") as conn:
        conn.execute("DROP TABLE selection")
        conn.execute("PRAGMA user_version = 1")
    conn.close()
    old = api.load_career(tmp_path, "sel")
    assert old.selection is None


def test_selection_survives_the_rollover_when_still_valid(career: Career, tmp_path: Path) -> None:
    api.confirm_selection(career, propose(career, "4-3-3"))
    api.continue_career(career, tmp_path, to_season_end=True)
    api.continue_career(career, tmp_path)  # rollover
    if career.selection is not None:  # still valid: same players at the club
        assert career.live_provider.team_sheet("alvorada").formation.name == "4-3-3"
    assert api.propose_selection(career).formation in ("4-3-3", "4-4-2")
