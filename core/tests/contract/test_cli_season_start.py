"""Contract: `season groups` and `season fixtures` (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_groups(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "groups")
    assert code == EXIT_OK
    for label in ("Grupo A", "Grupo B", "Grupo C"):
        assert label in out
    assert "Vale do Ouro" in out


def test_fixtures_by_round(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "fixtures", "--round", "1")
    assert code == EXIT_OK
    assert "Rodada 1" in out
    assert out.count(" x ") == 6


def test_fixtures_by_club(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "fixtures", "--club",
                     "vale-do-ouro")
    assert code == EXIT_OK
    assert out.count(" x ") == 8


def test_unknown_club_exits_3(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    argv = ["--data", str(sample_dir), "season", "fixtures", "--club", "nope"]
    assert main(argv) == EXIT_NOT_FOUND
