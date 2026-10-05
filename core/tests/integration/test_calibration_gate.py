"""The calibration gates (Constitution I; SC-001..SC-003)."""

import dataclasses
from pathlib import Path

import pytest

from manager_core import api
from manager_core.calibration import exploit
from manager_core.calibration.exploit import run_exploit
from manager_core.calibration.harness import CalibrationReport, run
from manager_core.domain.dataset import Dataset
from manager_core.quicksim.params import load_params

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


@pytest.fixture(scope="module")
def pr_report(world: Dataset) -> CalibrationReport:
    return run(world, "pr")


def test_pr_gate_passes_every_primary_target(pr_report: CalibrationReport) -> None:
    failing = {r.target.id: round(r.value, 3) for r in pr_report.results if r.verdict == "fail"}
    assert pr_report.passed, failing
    assert pr_report.league_matches == 20 * 132


def test_report_records_versions(pr_report: CalibrationReport) -> None:
    params = load_params()
    assert pr_report.model_version == params.model_version
    assert pr_report.params_hash == params.params_hash[:12]
    assert pr_report.core_version and pr_report.python_version


def test_caution_behaviour_reduces_second_yellows(pr_report: CalibrationReport) -> None:
    """SC-006: fewer second yellows with the behaviour on. The defensive cost is exact and
    tested at the rating level (test_quicksim_game_state); here it is only reported, because
    its effect on goals is smaller than the sample noise."""
    c = pr_report.caution
    assert c is not None
    assert c.second_yellow_rate_on <= 0.75 * c.second_yellow_rate_off
    assert c.conceded_on > 0 and c.conceded_off > 0


@pytest.mark.slow
def test_reports_are_byte_identical(world: Dataset, pr_report: CalibrationReport) -> None:
    # the exploit check is left out: it is deterministic on its own (below) and doubles the cost
    without = dataclasses.replace(pr_report, exploit=None)
    assert run(world, "pr", exploit=False).to_json() == without.to_json()


@pytest.mark.slow
def test_a_broken_parameter_fails_the_gate(world: Dataset) -> None:
    params = load_params()
    broken = params.with_values(**{"rates.shot": min(0.9, params.rates.shot * 2)})
    report = run(world, "pr", params=broken, exploit=False)
    assert not report.passed
    assert "goals_per_match" in report.failures


def test_the_exploit_check_is_deterministic(world: Dataset) -> None:
    """Same seeds, same points per match (on a tiny sample: the full one is in the PR gate)."""
    params = load_params()
    first = run_exploit(world, params, matches=(1, 1))
    assert first.ppm == run_exploit(world, params, matches=(1, 1)).ppm
    assert first.matches_per_venue == 1 and "stack" in first.ppm


def test_the_pooled_exploit_check_equals_the_serial_one(world: Dataset,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """Worker processes hold their own state (provider, caches): it must not change a result."""
    params = load_params()
    monkeypatch.setattr(exploit, "WORKERS", 1)
    serial = run_exploit(world, params, matches=(1, 1))
    monkeypatch.setattr(exploit, "WORKERS", 2)
    assert run_exploit(world, params, matches=(1, 1)).ppm == serial.ppm


@pytest.mark.slow
@pytest.mark.milestone
def test_milestone_gate_passes(world: Dataset) -> None:
    report = run(world, "milestone")
    failing = {r.target.id: round(r.value, 3) for r in report.results if r.verdict == "fail"}
    assert report.passed, failing
