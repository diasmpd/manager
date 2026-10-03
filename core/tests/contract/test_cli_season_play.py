"""Contract: season table / bracket / day / outcomes (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_group_table(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "--date", "2027-01-31",
                     "table", "--group", "A")
    assert code == EXIT_OK
    for key in ("table.pos", "table.club", "table.p", "table.w", "table.d", "table.l",
                "table.gf", "table.ga", "table.gd", "table.pts"):
        assert t(key) in out
    assert len([line for line in out.splitlines() if line.strip()]) == 3 + 4  # title, header, rule


def test_overall_table_marks_zones(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "table")
    assert code == EXIT_OK
    assert "Semifinal" in out
    assert t("zone.relegated") in out
    assert "Troféu Inconfidência" in out


def test_bracket(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "bracket")
    assert code == EXIT_OK
    assert "Semifinal" in out and "Final" in out
    assert "Troféu Inconfidência – final" in out
    assert "Arena Estadual das Gerais" in out
    assert t("season.provisional") in out


def test_day(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "day", "--date", "2027-01-10")
    assert code == EXIT_OK
    assert t("season.provisional") in out


def test_outcomes(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "outcomes")
    assert code == EXIT_OK
    for key in ("outcome.runner_up", "outcome.relegated"):
        assert t(key) in out
    assert "Campeão Mineiro:" in out and "Troféu Inconfidência:" in out


def test_unknown_group_exits_3(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    assert main(["--data", str(sample_dir), "season", "table", "--group", "Z"]) == EXIT_NOT_FOUND
