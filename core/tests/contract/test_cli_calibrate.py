"""Contract: `calibrate` (contracts/cli.md). Runs the PR gate, so it is marked slow."""

import json
from pathlib import Path

import pytest

from manager_core.calibration.targets import TARGETS_ENV, load_targets
from manager_core.cli import EXIT_INVALID, EXIT_OK, main
from manager_core.i18n import t

pytestmark = pytest.mark.slow


def test_calibrate_prints_every_target(capsys: pytest.CaptureFixture[str], sample_dir: Path,
                                       tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    code = main(["--data", str(sample_dir), "calibrate", "--write", str(report)])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    for target in load_targets():
        assert t(f"metric.{target.id}") in out
    assert t("calibration.passed") in out
    doc = json.loads(report.read_text("utf-8"))
    assert doc["passed"] is True and doc["gate"] == "pr"

    code = main(["--data", str(sample_dir), "calibrate", "--baseline", str(report)])
    assert code == EXIT_OK
    assert t("calibration.before") in capsys.readouterr().out


def test_failing_target_exits_1(capsys: pytest.CaptureFixture[str], sample_dir: Path,
                                tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    targets = tmp_path / "targets.toml"
    targets.write_text("""format_version = 1

[[targets]]
id = "goals_per_match"
sample = "league"
kind = "primary"
unit = "per_match"
target = 9.5
low = 9.0
high = 10.0
source = "teste"
retrieved = 2026-10-02
""", "utf-8")
    monkeypatch.setenv(TARGETS_ENV, str(targets))
    code = main(["--data", str(sample_dir), "calibrate"])
    out = capsys.readouterr().out
    assert code == EXIT_INVALID
    assert "goals_per_match" in out
