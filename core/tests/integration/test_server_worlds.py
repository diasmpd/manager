"""Choosing the world for a new career (spec 013 T001), on fictional data only: the data
repository here holds a copy of the sample with one club renamed, and a broken folder."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from manager_core import api
from manager_core.server.methods import Config

from .test_server_methods import SAMPLE, Client

RENAMED = "Alvorada da Cópia"
SHORT = "Copiado"


def _client(saves: Path, data_repo: Path | None) -> Client:
    client = Client(saves)
    client.session.state["config"] = Config(saves, SAMPLE, data_repo)
    return client


@pytest.fixture
def data_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "manager-data"
    copy = repo / "datasets" / "mineiro-copia"
    shutil.copytree(SAMPLE, copy)
    clubs = copy / "clubs.csv"
    clubs.write_bytes(clubs.read_bytes().replace("Grêmio Recreativo Alvorada;Alvorada;".encode(),
                                                 f"{RENAMED};{SHORT};".encode()))
    meta = copy / "dataset.csv"  # collected for the 2026 season, like a real build
    meta.write_bytes(meta.read_bytes().replace(b";2027-01-01;", b";2026-01-15;"))
    broken = repo / "datasets" / "aaa-quebrado"
    broken.mkdir(parents=True)
    (broken / "dataset.csv").write_text("format_version;reference_date\n1.0;ontem\n", "utf-8")
    (repo / "datasets" / "notas.txt").write_text("not a dataset", "utf-8")
    return repo


def test_the_sample_alone_without_a_data_repository(tmp_path: Path) -> None:
    for repo in (None, tmp_path / "missing"):
        worlds = _client(tmp_path / "saves", repo).call("worlds.list")
        assert [w["id"] for w in worlds] == ["sample"]
        assert worlds[0]["fictional"] is True and worlds[0]["clubs"] == 12


def test_the_worlds_of_a_data_repository(tmp_path: Path, data_repo: Path) -> None:
    worlds = _client(tmp_path / "saves", data_repo).call("worlds.list")
    assert [w["id"] for w in worlds] == ["sample", "mineiro-copia"]  # the broken one left out
    copy = worlds[1]
    assert copy["clubs"] == 12 and copy["players"] > 0 and copy["label"]
    assert (worlds[0]["reference_date"], copy["reference_date"]) == ("2027-01-01", "2026-01-15")


def test_clubs_and_careers_per_world(tmp_path: Path, data_repo: Path) -> None:
    client = _client(tmp_path / "saves", data_repo)
    sample_names = {c["id"]: c["name"] for c in client.call("career.clubs")}
    copy_names = {c["id"]: c["name"] for c in client.call("career.clubs", world="mineiro-copia")}
    assert sample_names["alvorada"] == "Grêmio Recreativo Alvorada"
    assert copy_names["alvorada"] == RENAMED
    status = client.call("career.new", name="copia", club_id="alvorada", world="mineiro-copia")
    assert status["club_name"] == SHORT
    # the save embeds its world: it opens the same once the folder is gone
    shutil.rmtree(data_repo / "datasets" / "mineiro-copia")
    reopened = _client(tmp_path / "saves", data_repo)
    assert reopened.call("career.open", name="copia")["status"]["club_name"] == SHORT
    career = api.load_career(tmp_path / "saves", "copia")
    assert career.world.clubs["alvorada"].name == RENAMED


def test_without_a_world_the_sample_is_used(tmp_path: Path, data_repo: Path) -> None:
    client = _client(tmp_path / "saves", data_repo)
    status = client.call("career.new", name="padrao", club_id="alvorada")
    assert status["club_name"] == "Alvorada"


def test_an_unknown_world(tmp_path: Path, data_repo: Path) -> None:
    client = _client(tmp_path / "saves", data_repo)
    for method, params in (("career.clubs", {}), ("career.new", {"name": "x",
                                                                 "club_id": "alvorada"})):
        error = client.error(method, world="aaa-quebrado", **params)
        assert error["data"]["kind"] == "world" and error["data"]["id"] == "aaa-quebrado"


def test_a_career_starts_in_its_worlds_year(tmp_path: Path, data_repo: Path) -> None:
    """Owner decision 2026-10-21: a real world plays the season its squads were collected for."""
    client = _client(tmp_path / "saves", data_repo)
    real = client.call("career.new", name="real", club_id="alvorada", world="mineiro-copia")
    sample = client.call("career.new", name="ficticio", club_id="alvorada")
    assert (real["year"], sample["year"]) == (2026, 2027)
    assert real["next_match"]["kickoff"].startswith("2026-01")
    assert sample["next_match"]["kickoff"].startswith("2027-01")
