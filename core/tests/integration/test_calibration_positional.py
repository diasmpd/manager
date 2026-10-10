"""The positional engine's calibration gates and cross-validation (spec 008 FR-008, FR-009).

The mechanics are tested on a handful of matches. The gates themselves are milestone checks
until the engine is fitted (T011); the PR gate then joins the CI run.
"""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.calibration import positional
from manager_core.calibration.harness import CalibrationReport, run
from manager_core.calibration.samples import league_fixtures
from manager_core.calibration.targets import load_targets
from manager_core.cli import EXIT_INVALID, EXIT_OK, main
from manager_core.domain.dataset import Dataset
from manager_core.i18n import t
from manager_core.positional.params import load_params as load_positional_params
from manager_core.quicksim.params import load_params

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
TINY = 2


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


@pytest.fixture
def tiny(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two matches in this process: starting worker processes would cost more than playing."""
    monkeypatch.setattr(positional, "MATCHES", {"pr": TINY, "milestone": TINY})
    monkeypatch.setattr(positional, "WORKERS", 1)


def test_the_sample_is_the_head_of_the_league_sample(world: Dataset) -> None:
    """Both engines play the same fixtures on the same random streams."""
    head = positional.fixtures(world, 300)
    assert len(head) == 300
    assert head == league_fixtures(world, 3)[:300]
    assert head[0].rng().random() == league_fixtures(world, 1)[0].rng().random()


def test_the_pr_gate_fails_only_on_robust_metrics(world: Dataset, tiny: None) -> None:
    report = run(world, "pr", engine="positional")
    assert report.engine == "positional" and report.league_matches == TINY
    assert report.state_matches == 0 and report.cross is None and report.exploit is None
    league = [target.id for target in load_targets() if target.sample == "league"]
    assert [r.target.id for r in report.results] == league
    for r in report.results:
        if r.verdict == "fail":
            assert r.target.primary and r.target.id in positional.ROBUST
    fitted = load_positional_params()
    assert report.model_version == f"positional {fitted.model_version}"
    assert report.params_hash == fitted.params_hash[:12]


def test_the_milestone_gate_cross_validates_on_the_same_fixtures(world: Dataset,
                                                                 tiny: None) -> None:
    report = run(world, "milestone", engine="positional")
    cross = report.cross
    assert cross is not None and cross.matches == TINY
    assert {row.id: row.tolerance for row in cross.rows} == positional.CROSS_TOLERANCES
    values = {r.target.id: r.value for r in report.results}
    for row in cross.rows:
        assert row.positional == values[row.id]
        assert row.ok == (abs(row.positional - row.quick) <= row.tolerance)
    assert report.passed == (cross.passed and all(r.verdict != "fail" for r in report.results))
    for r in report.results:  # every primary target gates at the milestone
        if r.target.primary and not r.target.contains(r.value):
            assert r.verdict == "fail"


def test_the_pooled_sample_equals_the_serial_one(world: Dataset,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """Worker processes hold their own state: it must not change a result, nor its order."""
    args = (world, load_params(), load_positional_params(), TINY)
    monkeypatch.setattr(positional, "WORKERS", 1)
    serial = positional.league_sample(*args)
    monkeypatch.setattr(positional, "WORKERS", 2)
    assert positional.league_sample(*args) == serial


def test_a_cross_validation_miss_fails_the_gate() -> None:
    base = {name: 0.2 for name in positional.CROSS_TOLERANCES}
    assert positional.cross_validate(base, base, 10).passed
    off = base | {"draw": 0.25}
    cross = positional.cross_validate(off, base, 10)
    assert not cross.passed and cross.failures == ["draw"]


def test_calibrate_engine_positional(capsys: pytest.CaptureFixture[str], tiny: None,
                                     tmp_path: Path) -> None:
    written = tmp_path / "report.json"
    code = main(["--data", str(SAMPLE), "calibrate", "--engine", "positional", "--gate",
                 "milestone", "--write", str(written)])
    out = capsys.readouterr().out
    assert code in (EXIT_OK, EXIT_INVALID)  # four matches cannot pass or fail meaningfully
    assert "motor posicional" in out and "Validação cruzada" in out
    assert t("metric.shootout_conversion") not in out  # the league sample only
    assert '"engine": "positional"' in written.read_text("utf-8")


@pytest.mark.slow
@pytest.mark.milestone
@pytest.mark.parametrize("gate", ["pr", "milestone"])
def test_positional_gate_passes(world: Dataset, gate: str) -> None:
    report: CalibrationReport = run(world, gate, engine="positional")
    assert report.passed, report.failures
