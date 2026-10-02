"""Contract: position rank, lineup suggest, formation list (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_position_rank(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "position", "rank", "vale-do-ouro", "DC")
    assert code == EXIT_OK
    for key in ("cli.col.player", "cli.col.band", "cli.col.suitability"):
        assert t(key) in out
    assert len(out.strip().splitlines()) == 2 + 27


def test_lineup_suggest(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "lineup", "suggest", "vale-do-ouro",
                     "--formation", "4-3-3")
    assert code == EXIT_OK
    for key in ("cli.col.slot", "cli.col.player", "cli.col.suitability"):
        assert t(key) in out
    assert t("cli.lineup.total", total="") in out


def test_formation_list(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _run(capsys, "formation", "list")
    assert code == EXIT_OK
    for name in ("4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2"):
        assert name in out


@pytest.mark.parametrize(
    "argv",
    [
        ["position", "rank", "vale-do-ouro", "XX"],
        ["position", "rank", "no-such-club", "DC"],
        ["lineup", "suggest", "no-such-club"],
        ["lineup", "suggest", "vale-do-ouro", "--formation", "2-3-5"],
    ],
)
def test_unknown_inputs_exit_3(
    capsys: pytest.CaptureFixture[str], sample_dir: Path, argv: list[str]
) -> None:
    assert main(["--data", str(sample_dir), *argv]) == EXIT_NOT_FOUND
