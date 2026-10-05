"""The user's tactic in the career (spec 006 US1, T013)."""

import dataclasses
import sqlite3
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import Career
from manager_core.career.store import FORMAT_VERSION, path_for
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


@pytest.fixture
def career(world: Dataset) -> Career:
    return api.new_career(world, "tac", "alvorada", master_seed=1)


def test_the_default_tactic_follows_the_selection(career: Career) -> None:
    sheet_formation = career.live_provider.team_sheet("alvorada").formation.name
    assert api.current_tactic(career).ip_formation == sheet_formation
    api.confirm_selection(career, api.propose_selection(career, "4-3-3"))
    tactic = api.current_tactic(career)
    assert tactic.ip_formation == "4-3-3"
    assert tactic.oop_formation == api.suggest_oop_formations("4-3-3")[0]
    assert api.validate_tactic(career, tactic) == []


def test_the_users_club_never_plays_an_ai_style(career: Career) -> None:
    provider = career.live_provider
    home = provider.team_sheet("alvorada")
    away = provider.team_sheet("serra-negra")
    mine, theirs = provider.tactics_for(home, away)
    assert mine is not None and mine.style is None
    assert theirs is not None and theirs.style is not None


def test_confirm_applies_and_refuses(career: Career) -> None:
    tactic = dataclasses.replace(api.current_tactic(career), mentality="attacking")
    api.confirm_tactic(career, tactic)
    assert career.tactic is not None and career.tactic.mentality == "attacking"
    sheet = career.live_provider.team_sheet("alvorada")
    assert career.live_provider.tactics_for(sheet, sheet)[0] == api.current_tactic(career)
    bad = dataclasses.replace(tactic, mentality="kamikaze")
    with pytest.raises(api.TacticError) as caught:
        api.confirm_tactic(career, bad)
    assert [i.code for i in caught.value.issues] == ["T001"]
    assert career.tactic.mentality == "attacking"  # unchanged


def test_a_taker_must_be_in_the_squad(career: Career, world: Dataset) -> None:
    tactic = api.current_tactic(career)
    outsider = next(m.player_id for m in world.memberships.values() if m.club_id != "alvorada")
    takers = tuple((k, outsider if k == tactic.set_pieces.takers[0][0] else v)
                   for k, v in tactic.set_pieces.takers)
    bad = dataclasses.replace(tactic, set_pieces=dataclasses.replace(tactic.set_pieces,
                                                                     takers=takers))
    assert [i.code for i in api.validate_tactic(career, bad)] == ["T004"]


def test_a_formation_change_keeps_the_instructions(career: Career) -> None:
    api.confirm_selection(career, api.propose_selection(career, "4-4-2"))
    tactic = dataclasses.replace(api.current_tactic(career), mentality="cautious")
    api.confirm_tactic(career, tactic)
    api.confirm_selection(career, api.propose_selection(career, "3-5-2"))
    refitted = api.current_tactic(career)
    assert refitted.ip_formation == "3-5-2" and refitted.mentality == "cautious"
    assert api.validate_tactic(career, refitted) == []


def test_role_helpers(career: Career, world: Dataset) -> None:
    roles = api.valid_roles("DC", "ip")
    assert roles and all("DC" in {p.value for p in r.positions} for r in roles)
    pid = next(p.id for p in world.squad("alvorada"))
    assert 1.0 <= api.role_suitability(career, pid, roles[0].id) <= 20.0
    with pytest.raises(api.NotFoundError):
        api.role_suitability(career, pid, "no_such_role")
    with pytest.raises(api.NotFoundError):
        api.suggest_oop_formations("9-0-1")
    assert len(api.tactic_options().mentality.settings) == 7


def test_tactic_survives_save_load_and_migration(career: Career, tmp_path: Path) -> None:
    tactic = dataclasses.replace(api.current_tactic(career), mentality="positive")
    api.confirm_tactic(career, tactic)
    api.save_career(career, tmp_path)
    loaded = api.load_career(tmp_path, "tac")
    assert loaded.tactic == career.tactic
    assert FORMAT_VERSION == 3
    # a format-2 save (005) has no tactic table: it is migrated and loads with the default
    with sqlite3.connect(path_for(tmp_path, "tac")) as conn:
        conn.execute("DROP TABLE tactic")
        conn.execute("PRAGMA user_version = 2")
    conn.close()
    old = api.load_career(tmp_path, "tac")
    assert old.tactic is None
    assert api.current_tactic(old).mentality == "balanced"


def test_the_owner_is_told_only_about_lost_choices(career: Career) -> None:
    from manager_core.domain.positions import Position
    from manager_core.tactics.catalogue import valid_roles

    api.confirm_selection(career, api.propose_selection(career, "4-4-2"))
    assert api.tactic_changes(career, "4-3-3") == []  # nothing confirmed yet
    api.confirm_tactic(career, api.current_tactic(career))
    assert api.tactic_changes(career, "4-4-2") == []  # same formation
    assert api.tactic_changes(career, "4-3-3") == []  # only defaults: nothing lost
    # a custom role on every slot: the slots without a place in 4-3-3 lose it
    tactic = api.current_tactic(career)
    positions = api.formation_positions("4-4-2")
    slots = tuple(dataclasses.replace(
        s, ip_role=[r.id for r in valid_roles(Position(positions[s.slot]), "ip")][-1])
        for s in tactic.slots)
    api.confirm_tactic(career, dataclasses.replace(tactic, slots=slots))
    changes = api.tactic_changes(career, "4-3-3")
    assert changes and set(changes) <= set(positions)
    assert "GK" not in changes and "DC" not in changes  # both still exist in 4-3-3


def test_an_invalid_saved_tactic_falls_back_to_the_default(career: Career,
                                                          tmp_path: Path) -> None:
    api.confirm_tactic(career, dataclasses.replace(api.current_tactic(career),
                                                   mentality="positive"))
    api.save_career(career, tmp_path)
    with sqlite3.connect(path_for(tmp_path, "tac")) as conn:  # a role renamed in the data
        (text,) = conn.execute("SELECT tactic_json FROM tactic").fetchone()
        role = career.tactic.slots[0].ip_role
        conn.execute("UPDATE tactic SET tactic_json = ?",
                     (text.replace(f'"{role}"', '"renamed_role"'),))
    conn.close()
    loaded = api.load_career(tmp_path, "tac")
    assert loaded.tactic is None
    assert loaded.notices and "padrão" in loaded.notices[0]
    assert api.current_tactic(loaded).mentality == "balanced"
