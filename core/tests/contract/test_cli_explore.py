"""Contract: CLI browsing commands (contracts/cli.md)."""

import dataclasses
from pathlib import Path

import pytest

from manager_core import api
from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


@pytest.fixture(scope="module")
def first_club(sample_dir_module: Path) -> str:
    dataset = api.load_dataset(sample_dir_module).dataset
    assert dataset is not None
    return next(iter(dataset.clubs))


@pytest.fixture(scope="module")
def sample_dir_module() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "sample"


def test_club_list(capsys: pytest.CaptureFixture[str], sample_dir_module: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir_module), "club", "list")
    assert code == EXIT_OK
    for key in ("cli.col.id", "cli.col.name", "cli.col.abbr", "cli.col.squad_size", "cli.col.avg_ca"):
        assert t(key) in out
    assert len(out.strip().splitlines()) == 2 + 12


@pytest.mark.parametrize("sort", ["position", "ca", "age", "number"])
def test_club_squad_sorts(
    capsys: pytest.CaptureFixture[str], sample_dir_module: Path, first_club: str, sort: str
) -> None:
    code, out = _run(capsys, "--data", str(sample_dir_module), "club", "squad", first_club,
                     "--sort", sort)
    assert code == EXIT_OK
    for key in ("cli.col.number", "cli.col.player", "cli.col.age", "cli.col.position",
                "cli.col.band", "cli.col.suitability", "cli.col.ca"):
        assert t(key) in out


def test_player_show_hides_hidden_by_default(
    capsys: pytest.CaptureFixture[str], sample_dir_module: Path
) -> None:
    code, out = _run(capsys, "--data", str(sample_dir_module), "player", "show", "p-000001")
    assert code == EXIT_OK
    assert t("cli.ca") in out
    assert t("cli.pa") not in out
    assert t("attr.temperament") not in out
    code, out = _run(capsys, "--data", str(sample_dir_module), "player", "show", "p-000001",
                     "--hidden")
    assert code == EXIT_OK
    assert t("cli.pa") in out
    assert t("attr.temperament") in out


def test_unknown_ids_exit_3(capsys: pytest.CaptureFixture[str], sample_dir_module: Path) -> None:
    assert main(["--data", str(sample_dir_module), "club", "squad", "no-such-club"]) == EXIT_NOT_FOUND
    assert main(["--data", str(sample_dir_module), "player", "show", "p-999999"]) == EXIT_NOT_FOUND


def test_duplicate_display_names_are_disambiguated(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, sample_dir_module: Path, first_club: str
) -> None:
    dataset = api.load_dataset(sample_dir_module).dataset
    assert dataset is not None
    a, b = dataset.squad(first_club)[:2]
    players = dict(dataset.players)
    players[a.id] = dataclasses.replace(a, display_name="Zé Teste")
    players[b.id] = dataclasses.replace(b, display_name="Zé Teste")
    out_dir = tmp_path / "dup"
    api.export_dataset(dataclasses.replace(dataset, players=players), out_dir)

    entries = api.squad(api.load_dataset(out_dir).dataset, first_club)  # type: ignore[arg-type]
    labels = [e.label for e in entries if e.display_name == "Zé Teste"]
    assert len(labels) == 2 and len(set(labels)) == 2
    code, out = _run(capsys, "--data", str(out_dir), "club", "squad", first_club)
    assert code == EXIT_OK
    assert all(label in out for label in labels)
