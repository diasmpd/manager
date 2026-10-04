"""Fit the quick-sim parameters to the calibration targets (research R9). Dev-only.

Coordinate descent with multiplicative steps on a fixed tuning sample (common random numbers,
so the objective is deterministic). The loss is the sum of squared distances to each target,
in units of half its band; secondary targets weigh less.

    python tools/tune_quicksim.py [--rounds 4] [--write]

`--write` saves the fitted parameters to reference/quicksim/model.toml. It tunes on the PR-gate
sample; always confirm with the milestone gate (`calibrate --gate milestone`), which uses other
seeds and five times the matches.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from manager_core import api
from manager_core.calibration.harness import measure
from manager_core.calibration.samples import GATES, SampleSpec
from manager_core.calibration.targets import load_targets
from manager_core.domain.dataset import Dataset
from manager_core.quicksim.params import ModelParams, dump_params, load_params
from manager_core.quicksim.provider import QuickSimProvider

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "manager_core" / "reference" / "quicksim" / "model.toml"
# Coarse rounds on a fast sample, then (--polish) on the PR-gate sample; the milestone gate
# (other seeds, 5x larger) is the out-of-sample check against overfitting.
FAST = SampleSpec("fast", league_seasons=12, mineiro_seasons=12)
SECONDARY_WEIGHT = 0.3

# (dotted parameter path, lower bound, upper bound)
TUNABLE = [
    ("rates.shot", 0.03, 0.4),
    ("time.trend_start", 0.6, 1.0),  # tempo rises within each half (bounds keep start <= end)
    ("time.trend_end", 1.0, 1.6),
    ("time.second_half", 0.9, 1.4),
    ("strength.xg_median", 0.02, 0.3),
    ("home.shot", 1.0, 1.6),
    ("home.away_shot", 0.6, 1.0),
    ("state.level", 0.0, 0.5),  # at most state.chase: trailing pushes at least as hard
    ("state.settled", 0.0, 0.35),  # pulls blowouts back toward the middle totals
    ("shootout.base", 0.6, 0.85),
    ("strength.attack", 0.02, 1.0),
    ("strength.control", 0.0, 1.0),
    ("strength.xg_attack", 0.0, 1.0),
    ("rates.yellow_per_foul", 0.05, 0.5),
    ("rates.direct_red_per_foul", 0.0005, 0.02),
    ("caution.card", 0.05, 0.95),  # full ease-off; player strength scales it
    ("caution.foul", 0.05, 0.95),
    ("rates.corner_per_shot", 0.05, 0.8),
    ("rates.own_goal_share", 0.005, 0.1),
]


def _get(params: ModelParams, path: str) -> float:
    obj: object = params
    for part in path.split("."):
        obj = getattr(obj, part)
    assert isinstance(obj, float)
    return obj


def loss(values: dict[str, float]) -> float:
    total = 0.0
    for t in load_targets():
        half = (t.high - t.low) / 2
        weight = 1.0 if t.primary else SECONDARY_WEIGHT
        total += weight * ((values[t.id] - t.target) / half) ** 2
    return total


TUNING = FAST


def evaluate(dataset: Dataset, provider: QuickSimProvider, params: ModelParams) -> float:
    values, *_ = measure(dataset, TUNING, params, caution=False, provider=provider)
    return loss(values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--version", default=None)
    parser.add_argument("--polish", action="store_true", help="tune on the PR-gate sample")
    args = parser.parse_args()
    global TUNING
    TUNING = GATES["pr"] if args.polish else FAST
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    dataset = loaded.dataset
    provider = QuickSimProvider(dataset)
    params = load_params()
    best = evaluate(dataset, provider, params)
    print(f"start loss {best:.3f}")
    step = 1.3
    for round_index in range(args.rounds):
        start = time.time()
        for path, low, high in TUNABLE:
            current = _get(params, path)
            for factor in (step, 1 / step):
                value = min(high, max(low, current * factor if current else low))
                if value == current:
                    continue
                trial = params.with_values(**{path: value})
                score = evaluate(dataset, provider, trial)
                if score < best:
                    best, params, current = score, trial, value
                    print(f"  {path} -> {value:.5f}  loss {best:.3f}", flush=True)
                    break
        print(f"round {round_index + 1}: loss {best:.3f} (step {step:.3f}, "
              f"{time.time() - start:.0f} s)", flush=True)
        step = 1 + (step - 1) * 0.6
    if args.version:
        params = params.with_values(model_version=args.version)  # type: ignore[arg-type]
    print(dump_params(params))
    if args.write:
        MODEL.write_text(_with_header(dump_params(params)), "utf-8")
        print(f"written to {MODEL}")


def _with_header(text: str) -> str:
    header = ("# Quick-sim model parameters (spec 003, research R9). Fitted by "
              "core/tools/tune_quicksim.py\n# against reference/calibration/quicksim-targets.toml."
              " Do not edit by hand without re-running\n# the calibration gate.\n")
    return header + text


if __name__ == "__main__":
    main()
