"""Contract: `season calendar [--month 1-12]` (contracts/cli.md)."""

from pathlib import Path

import pytest

from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t


def test_year_summary(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    assert main(["--data", str(sample_dir), "season", "calendar"]) == EXIT_OK
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 12
    for month, line in enumerate(lines, start=1):
        assert line.startswith(t(f"month.{month}").capitalize())
    assert "Carnaval" in lines[1] and "Data FIFA" in lines[2]


def test_february_day_by_day(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    assert main(["--data", str(sample_dir), "season", "calendar", "--month", "2"]) == EXIT_OK
    out = capsys.readouterr().out
    for day in range(1, 29):
        assert f"{day:02d}/02/2027" in out
    assert "[Carnaval" in out
    assert t("season.provisional") not in out  # quick-sim results are final (003)


def test_held_dates_before_pairing(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code = main(["--data", str(sample_dir), "season", "--date", "2027-01-20", "calendar",
                 "--month", "3"])
    assert code == EXIT_OK
    assert t("calendar.reserved", stage="Final") in capsys.readouterr().out


def test_month_13_exits_3(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    assert main(["--data", str(sample_dir), "season", "calendar", "--month", "13"]) \
        == EXIT_NOT_FOUND
