"""US1: start a career and save it (spec 004, contracts/save-format.md)."""

import os
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import Career
from manager_core.career.store import FORMAT_VERSION, SaveError
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _views(career: Career) -> tuple:
    season = career.season
    return (
        career.name, career.master_seed, career.user_club_id, career.current_date,
        [(g.label, g.club_ids) for g in api.season_groups(season)],
        [(m.id, m.kickoff, m.result) for m in api.season_fixtures(season)],
        [(r.club_id, r.points, r.goal_difference) for r in api.season_table(season)],
        sorted(career.world.players), career.world.reference_date,
    )


def test_new_career_saves_and_loads_identically(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "teste", "alvorada", master_seed=7)
    assert career.user_club_id == "alvorada"
    first_match = min(m.kickoff for m in career.season.matches.values())
    assert career.current_date < first_match.date()
    path = api.save_career(career, tmp_path)
    assert path == tmp_path / "teste.sqlite" and path.is_file()
    loaded = api.load_career(tmp_path, "teste")
    assert _views(loaded) == _views(career)


def test_played_results_survive_a_round_trip(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "meio", "serra-negra", master_seed=3)
    career.season.advance_to(date(2027, 2, 1))
    career.current_date = date(2027, 2, 1)
    api.save_career(career, tmp_path)
    loaded = api.load_career(tmp_path, "meio")
    assert loaded.season.results == career.season.results
    assert _views(loaded) == _views(career)


def test_save_as_is_an_independent_copy(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "original", "alvorada", master_seed=1)
    api.save_career(career, tmp_path)
    api.save_career(career, tmp_path, name="copia")
    names = [s.name for s in api.list_saves(tmp_path)]
    assert sorted(names) == ["copia", "original"]
    api.delete_save(tmp_path, "copia")
    assert [s.name for s in api.list_saves(tmp_path)] == ["original"]
    assert api.load_career(tmp_path, "original").name == "original"


def test_newer_format_is_refused(world: Dataset, tmp_path: Path) -> None:
    api.save_career(api.new_career(world, "novo", "alvorada", master_seed=1), tmp_path)
    with sqlite3.connect(tmp_path / "novo.sqlite") as conn:
        conn.execute(f"PRAGMA user_version = {FORMAT_VERSION + 1}")
    with pytest.raises(SaveError) as info:
        api.load_career(tmp_path, "novo")
    assert info.value.code == "V001"


def test_result_for_an_unknown_match_is_corrupt(world: Dataset, tmp_path: Path) -> None:
    api.save_career(api.new_career(world, "ruim", "alvorada", master_seed=1), tmp_path)
    with sqlite3.connect(tmp_path / "ruim.sqlite") as conn:
        conn.execute("INSERT INTO results VALUES ('nao-existe', '{}')")
    with pytest.raises(SaveError) as info:
        api.load_career(tmp_path, "ruim")
    assert info.value.code == "V003"


def test_failed_write_keeps_the_previous_save(world: Dataset, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    career = api.new_career(world, "seguro", "alvorada", master_seed=1)
    api.save_career(career, tmp_path)
    before = (tmp_path / "seguro.sqlite").read_bytes()

    def boom(src: str, dst: str) -> None:
        raise OSError("disk full")

    career.season.advance_to(date(2027, 2, 1))
    career.current_date = date(2027, 2, 1)
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        api.save_career(career, tmp_path)
    monkeypatch.undo()
    assert (tmp_path / "seguro.sqlite").read_bytes() == before
    assert api.load_career(tmp_path, "seguro").current_date < date(2027, 2, 1)


def test_bad_names(world: Dataset, tmp_path: Path) -> None:
    career = api.new_career(world, "ok", "alvorada", master_seed=1)
    for bad in ("Com Espaço", "autosave", "", "x" * 41):
        with pytest.raises(SaveError):
            api.save_career(career, tmp_path, name=bad)
    with pytest.raises(api.NotFoundError):
        api.load_career(tmp_path, "nada")
    with pytest.raises(api.NotFoundError):
        api.new_career(world, "x", "clube-inexistente")


def test_list_shows_the_career_date_not_today(world: Dataset, tmp_path: Path) -> None:
    """Regression: `current_date` is an SQLite keyword, so the list showed today's date."""
    career = api.new_career(world, "data", "alvorada", master_seed=1)
    career.season.advance_to(date(2027, 1, 20))
    career.current_date = date(2027, 1, 20)
    api.save_career(career, tmp_path)
    [summary] = api.list_saves(tmp_path)
    assert summary.current_date == date(2027, 1, 20)
