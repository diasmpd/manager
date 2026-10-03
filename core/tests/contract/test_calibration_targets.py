"""Contract: the calibration targets file (contracts/calibration-targets.md)."""

from pathlib import Path

import pytest

from manager_core.calibration.targets import (
    METRIC_IDS,
    TargetsError,
    load_targets,
    load_targets_file,
)


def test_bundled_targets_cover_every_metric_with_sources() -> None:
    targets = load_targets()
    assert sorted(t.id for t in targets) == sorted(METRIC_IDS)
    assert all(t.source and t.retrieved.isoformat() == "2026-10-02" for t in targets)


@pytest.mark.parametrize(("metric", "target", "low", "high"), [
    ("goals_per_match", 2.50, 2.30, 2.70),
    ("home_win", 0.486, 0.446, 0.526),
    ("draw", 0.261, 0.221, 0.301),
    ("away_win", 0.253, 0.213, 0.293),
    ("yellows_per_match", 5.2, 4.5, 6.0),
    ("reds_per_match", 0.25, 0.17, 0.33),
    ("mineiro_draw", 0.29, 0.22, 0.36),
])
def test_values_match_the_spec(metric: str, target: float, low: float, high: float) -> None:
    t = next(t for t in load_targets() if t.id == metric)
    assert (t.target, t.low, t.high) == (target, low, high)
    assert t.primary


ROW = """sample = "league"
kind = "primary"
unit = "per_match"
source = "x"
retrieved = 2026-10-02
"""


def _file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "targets.toml"
    path.write_text("format_version = 1\n\n[[targets]]\n" + body + ROW, "utf-8")
    return path


def test_unknown_metric_is_c001(tmp_path: Path) -> None:
    path = _file(tmp_path, 'id = "nope"\ntarget = 1.0\nlow = 0.5\nhigh = 1.5\n')
    with pytest.raises(TargetsError) as info:
        load_targets_file(path)
    assert info.value.problems == ["targets[0].id"]


def test_target_outside_band_is_c001(tmp_path: Path) -> None:
    path = _file(tmp_path, 'id = "goals_per_match"\ntarget = 3.0\nlow = 2.3\nhigh = 2.7\n')
    with pytest.raises(TargetsError) as info:
        load_targets_file(path)
    assert info.value.problems == ["targets[0].target"]
