"""The goal-total distribution of the positional engine, with and without the relaxed-leader
mechanism (spec 008 T013, research R5). Dev-only.

Plays every ordered pair of sample clubs `--seeds` times on the same seeds in both arms, so the
comparison is paired, and prints the share of each total (0..5+), the 3-goal share and the
variance/mean ratio next to the real targets (Série A 2024-25).

    python tools/goal_spread.py [--seeds 4]
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from itertools import permutations
from pathlib import Path

from manager_core import api
from manager_core.positional.engine import LiveMatch
from manager_core.positional.params import PositionalParams, load_params
from manager_core.quicksim.provider import QuickSimProvider

ROOT = Path(__file__).resolve().parents[1]
REAL_THREE = 0.245  # share of matches with exactly 3 goals

_worker: QuickSimProvider | None = None


def _init_worker() -> None:
    global _worker
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    _worker = QuickSimProvider(loaded.dataset)


def _play(home: str, away: str, seed: str, params: PositionalParams) -> tuple[int, int]:
    assert _worker is not None
    p = _worker
    hs, as_ = p.team_sheet(home), p.team_sheet(away)
    ht, at = p.tactics_for(hs, as_)
    match = LiveMatch(hs, as_, p.dataset.players, params, p.params, random.Random(seed),
                      False, ht, at, record=False)
    match.play()
    report = match.report()
    return report.home.goals, report.away.goals


def summary(name: str, scores: list[tuple[int, int]]) -> str:
    totals = [h + a for h, a in scores]
    n = len(totals)
    shares = [sum(t == k for t in totals) / n for k in range(5)] + [sum(t >= 5 for t in totals) / n]
    mean = statistics.fmean(totals)
    ratio = statistics.pvariance(totals) / mean if mean else 0.0
    cells = " ".join(f"{k}:{s:.3f}" for k, s in zip(["0", "1", "2", "3", "4", "5+"], shares,
                                                    strict=True))
    return f"{name:8} n={n} mean={mean:.2f} var/mean={ratio:.2f}  {cells}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=4)
    args = parser.parse_args()
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    pairs = list(permutations(sorted(loaded.dataset.clubs), 2))
    jobs = [(h, a, f"spread:{h}:{a}:{k}") for h, a in pairs for k in range(args.seeds)]
    on = load_params()
    off = on.with_values(**{"intents.relaxed_drop": 0.0, "intents.relaxed_risk": 0.0})
    with ProcessPoolExecutor(os.cpu_count() or 1, initializer=_init_worker) as pool:
        results = {}
        for name, params in (("off", off), ("on", on)):
            homes, aways, seeds = zip(*jobs, strict=True)
            results[name] = list(pool.map(_play, homes, aways, seeds, [params] * len(jobs),
                                          chunksize=4))
            print(summary(name, results[name]), flush=True)
    print(f"real 3-goal share {REAL_THREE}")


if __name__ == "__main__":
    main()
