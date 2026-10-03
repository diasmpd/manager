"""Contract: the `career` commands and `season --career` (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_INVALID, EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_career_flow(capsys: pytest.CaptureFixture[str], sample_dir: Path,
                     tmp_path: Path) -> None:
    base = ("--data", str(sample_dir), "--saves", str(tmp_path))
    code, out = _run(capsys, *base, "career", "new", "teste", "--club", "alvorada")
    assert code == EXIT_OK
    assert "Alvorada" in out and t("career.next_match") in out
    assert (tmp_path / "teste.sqlite").is_file()

    code, out = _run(capsys, *base, "career", "list")
    assert code == EXIT_OK and "teste" in out

    code, out = _run(capsys, *base, "career", "status", "teste")
    assert code == EXIT_OK and t("career.no_suspensions") in out

    stops = 0
    while True:
        code, out = _run(capsys, *base, "career", "continue", "teste")
        assert code == EXIT_OK
        stops += 1
        if t("career.stop.user_match") in out:
            break
        assert stops < 10
    code, out = _run(capsys, *base, "season", "--career", "teste", "table")
    assert code == EXIT_OK and t("table.pts") in out

    code, out = _run(capsys, *base, "career", "continue", "teste", "--to-season-end")
    assert code == EXIT_OK and t("career.stop.season_end", year=2027) in out

    code, out = _run(capsys, *base, "career", "continue", "teste")  # rollover
    assert code == EXIT_OK
    code, out = _run(capsys, *base, "career", "history", "teste")
    assert code == EXIT_OK and "2027" in out

    code, out = _run(capsys, *base, "career", "save", "teste", "--as", "copia")
    assert code == EXIT_OK and (tmp_path / "copia.sqlite").is_file()
    code, out = _run(capsys, *base, "career", "delete", "copia")
    assert code == EXIT_OK and not (tmp_path / "copia.sqlite").exists()


def test_errors(capsys: pytest.CaptureFixture[str], sample_dir: Path, tmp_path: Path) -> None:
    base = ("--data", str(sample_dir), "--saves", str(tmp_path))
    assert main([*base, "career", "status", "nada"]) == EXIT_NOT_FOUND
    assert main([*base, "career", "new", "x", "--club", "ninguem"]) == EXIT_NOT_FOUND
    assert main([*base, "career", "new", "Nome Ruim", "--club", "alvorada"]) == EXIT_INVALID
