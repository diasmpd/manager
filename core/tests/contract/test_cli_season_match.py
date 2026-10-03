"""Contract: `season match`, `season scorers` and match ids in fixtures (contracts/cli.md)."""

import re
from pathlib import Path

import pytest

from manager_core.cli import EXIT_NOT_FOUND, EXIT_OK, main
from manager_core.i18n import t

STATS = ("shots", "shots_on_target", "xg", "possession", "corners", "fouls", "yellows", "reds")


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_fixtures_show_match_ids(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "fixtures", "--round", "1")
    assert code == EXIT_OK
    assert "[primeira-fase-r01-01]" in out


def test_match_report(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    for n in range(1, 7):  # find a round-1 match with goals
        code, out = _run(capsys, "--data", str(sample_dir), "season", "match",
                         f"primeira-fase-r01-{n:02d}")
        assert code == EXIT_OK
        for key in STATS:
            assert t(f"stat.{key}") in out
        if t("match.goals") in out:
            goal_lines = out.split(t("match.goals"))[1].splitlines()[1:]
            assert re.match(r"\s+\d+(\+\d+)?'\s+\S", goal_lines[0])
            return
    pytest.fail("no round-1 match with goals")


def test_unknown_match_exits_3(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    assert main(["--data", str(sample_dir), "season", "match", "nope"]) == EXIT_NOT_FOUND


def test_match_not_played_yet(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "--date", "2027-01-02",
                     "match", "primeira-fase-r01-01")
    assert code == EXIT_OK
    assert t("match.not_played") in out


def test_scorers(capsys: pytest.CaptureFixture[str], sample_dir: Path) -> None:
    code, out = _run(capsys, "--data", str(sample_dir), "season", "scorers", "--limit", "5")
    assert code == EXIT_OK
    for key in ("pos", "player", "club", "goals", "penalties", "assists"):
        assert t(f"scorers.{key}") in out
    rows = [line for line in out.splitlines()[2:] if line.strip()]
    assert len(rows) == 5
    goals = [int(re.split(r"\s{2,}", r.strip())[3]) for r in rows]
    assert goals == sorted(goals, reverse=True)
