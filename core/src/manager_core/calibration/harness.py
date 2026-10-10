"""The calibration harness (FR-014..FR-018, research R10).

`run` simulates the gate's fixed samples, measures every target and returns a report. The
report is canonical JSON (sorted keys, 4-decimal floats), so the same code and inputs give
byte-identical files (SC-003).
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from manager_core import __version__
from manager_core.calibration import positional as positional_sample
from manager_core.calibration.exploit import ExploitReport, run_exploit
from manager_core.calibration.metrics import caution_check, league_metrics, mineiro_metrics
from manager_core.calibration.positional import CrossValidation, cross_validate
from manager_core.calibration.samples import (
    GATES,
    SampleSpec,
    league_sample,
    mineiro_sample,
)
from manager_core.calibration.targets import CalibrationTarget, load_targets
from manager_core.domain.dataset import Dataset
from manager_core.positional.params import PositionalParams
from manager_core.positional.params import load_params as load_positional_params
from manager_core.quicksim.params import ModelParams, load_params
from manager_core.quicksim.provider import QuickSimProvider

CAUTION_SEASONS = 10  # league seasons replayed with the caution behaviour off
ENGINES = ("quick", "positional")


@dataclass(frozen=True, slots=True)
class MetricResult:
    target: CalibrationTarget
    value: float
    verdict: str  # pass / fail / warn
    before: float | None = None


@dataclass(frozen=True, slots=True)
class CautionCheck:
    second_yellow_rate_on: float
    second_yellow_rate_off: float
    conceded_on: float
    conceded_off: float


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    core_version: str
    python_version: str
    model_version: str
    params_hash: str
    gate: str
    league_matches: int
    state_matches: int
    results: tuple[MetricResult, ...]
    caution: CautionCheck | None
    exploit: ExploitReport | None = None  # spec 006: the PR gate's tactical exploit check
    engine: str = "quick"
    cross: CrossValidation | None = None  # spec 008: the positional milestone gate

    @property
    def passed(self) -> bool:
        exploit_ok = self.exploit is None or self.exploit.passed
        cross_ok = self.cross is None or self.cross.passed
        return exploit_ok and cross_ok and all(r.verdict != "fail" for r in self.results)

    @property
    def failures(self) -> list[str]:
        failed = [r.target.id for r in self.results if r.verdict == "fail"]
        if self.exploit is not None and not self.exploit.passed:
            failed.append("tactical_exploit")
        if self.cross is not None:
            failed += [f"cross_validation:{name}" for name in self.cross.failures]
        return failed

    def to_json(self) -> str:
        def num(x: float | None) -> float | None:
            return None if x is None else round(x, 4)

        doc: dict[str, Any] = {
            "core_version": self.core_version,
            "engine": self.engine,
            "python_version": self.python_version,
            "model_version": self.model_version,
            "params_hash": self.params_hash,
            "gate": self.gate,
            "league_matches": self.league_matches,
            "state_matches": self.state_matches,
            "passed": self.passed,
            "metrics": {r.target.id: {"value": num(r.value), "target": r.target.target,
                                      "low": r.target.low, "high": r.target.high,
                                      "kind": r.target.kind, "verdict": r.verdict}
                        for r in self.results},
        }
        if self.exploit is not None:
            e = self.exploit
            best, gain = e.best
            doc["exploit"] = {
                "matches_per_venue": e.matches_per_venue, "passed": e.passed,
                "best": best, "best_gain": num(gain), "dominant": e.dominant,
                "ppm": {tactic: {style: num(v) for style, v in row.items()}
                        for tactic, row in e.ppm.items()},
            }
        if self.cross is not None:
            doc["cross_validation"] = {
                "matches": self.cross.matches, "passed": self.cross.passed,
                "metrics": {row.id: {"positional": num(row.positional), "quick": num(row.quick),
                                     "tolerance": row.tolerance, "ok": row.ok}
                            for row in self.cross.rows},
            }
        if self.caution is not None:
            doc["caution"] = {k: num(getattr(self.caution, k)) for k in (
                "second_yellow_rate_on", "second_yellow_rate_off", "conceded_on",
                "conceded_off")}
        return json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _baseline_values(path: Path | None) -> dict[str, float]:
    if path is None or not path.is_file():
        return {}
    doc = json.loads(path.read_text("utf-8"))
    return {k: v["value"] for k, v in doc.get("metrics", {}).items() if v.get("value") is not None}


def measure(dataset: Dataset, spec: SampleSpec, params: ModelParams, caution: bool = True,
            provider: QuickSimProvider | None = None,
            ) -> tuple[dict[str, float], int, int, CautionCheck | None]:
    provider = provider.with_params(params) if provider else QuickSimProvider(dataset, params)
    league = league_sample(dataset, provider, spec.league_seasons)
    seasons = mineiro_sample(dataset, provider, spec.mineiro_seasons)
    values = league_metrics(league) | mineiro_metrics(seasons)
    check = None
    if caution:
        off = params.with_values(**{"caution.enabled": not params.caution.enabled})
        off_league = league_sample(dataset, provider.with_params(off), CAUTION_SEASONS)
        on_rate, on_cost = caution_check(
            [m for m in league if m.season < CAUTION_SEASONS])
        off_rate, off_cost = caution_check(off_league)
        if not params.caution.enabled:
            on_rate, off_rate, on_cost, off_cost = off_rate, on_rate, off_cost, on_cost
        check = CautionCheck(on_rate, off_rate, on_cost, off_cost)
    state_matches = sum(len(s.results) for s in seasons)
    return values, len(league), state_matches, check


def _run_positional(dataset: Dataset, gate: str, params: ModelParams,
                    positional: PositionalParams, baseline: Path | None) -> CalibrationReport:
    """The positional engine's gate (spec 008, research R6): the league targets on its own
    sample, and at the milestone the cross-validation with the quick sim on the same fixtures."""
    n = positional_sample.MATCHES[gate]
    played = positional_sample.league_sample(dataset, params, positional, n)
    values = league_metrics(played)
    before = _baseline_values(baseline)
    results = []
    for target in load_targets():
        if target.sample != "league":
            continue
        value = values[target.id]
        gating = target.primary and (gate == "milestone" or target.id in positional_sample.ROBUST)
        verdict = "pass" if target.contains(value) else ("fail" if gating else "warn")
        results.append(MetricResult(target, value, verdict, before.get(target.id)))
    cross = None
    if gate == "milestone":
        seasons = played[-1].season + 1
        quick = league_sample(dataset, QuickSimProvider(dataset, params), seasons)[:n]
        cross = cross_validate(values, league_metrics(quick), n)
    return CalibrationReport(__version__, platform.python_version(),
                             f"positional {positional.model_version}",
                             positional.params_hash[:12], gate, len(played), 0, tuple(results),
                             None, engine="positional", cross=cross)


def run(dataset: Dataset, gate: str = "pr", params: ModelParams | None = None,
        baseline: Path | None = None, exploit: bool | None = None, engine: str = "quick",
        positional: PositionalParams | None = None) -> CalibrationReport:
    """`exploit` (default: on for the PR gate) adds the tactical exploit check. `engine` is
    "quick" or "positional"; the positional gate has no exploit check yet."""
    if gate not in GATES:
        raise ValueError(f"unknown gate {gate!r}")
    if engine not in ENGINES:
        raise ValueError(f"unknown engine {engine!r}")
    params = params or load_params()
    if engine == "positional":
        return _run_positional(dataset, gate, params, positional or load_positional_params(),
                               baseline)
    values, n_league, n_mineiro, check = measure(dataset, GATES[gate], params)
    before = _baseline_values(baseline)
    results = []
    for target in load_targets():
        value = values[target.id]
        verdict = "pass" if target.contains(value) else ("fail" if target.primary else "warn")
        results.append(MetricResult(target, value, verdict, before.get(target.id)))
    if exploit is None:
        exploit = gate == "pr"
    check_exploit = run_exploit(dataset, params, gate) if exploit else None
    return CalibrationReport(__version__, platform.python_version(), params.model_version,
                             params.params_hash[:12], gate, n_league, n_mineiro,
                             tuple(results), check, check_exploit)
