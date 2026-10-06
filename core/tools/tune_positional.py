"""Fit the positional engine's parameters to real-football targets (spec 008 T011). Dev-only.

Coordinate descent with multiplicative steps on a fixed, seeded fixture set (common random
numbers, so the objective is deterministic). The loss is the sum of squared distances to each
target in units of its tolerance; secondary targets weigh less.

    python tools/tune_positional.py [--rounds 3] [--fixtures 66] [--write]

Targets are the quick sim's calibration targets (Série A 2024-25, 760-match recount) plus
passing volume and completion (secondary, typical top-flight values, to be sourced).
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import permutations
from pathlib import Path

from manager_core import api
from manager_core.positional.engine import LiveMatch
from manager_core.positional.params import PositionalParams, load_params
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import MatchReport
from manager_core.tactics.model import default_tactic

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "manager_core" / "reference" / "positional" / "model.toml"

# metric -> (target, tolerance, weight); per match unless noted
TARGETS = {
    "goals": (2.48, 0.2, 1.0),
    "home_goals": (1.47, 0.15, 1.0),
    "away_goals": (1.02, 0.15, 1.0),
    "shots": (25.0, 4.0, 1.0),
    "on_target_per_side": (4.2, 0.75, 1.0),
    "xg_per_shot": (0.10, 0.02, 1.0),
    "corners": (9.8, 1.25, 0.5),
    "fouls": (26.0, 4.0, 0.5),
    "yellows": (5.2, 0.75, 0.5),
    "reds": (0.25, 0.08, 0.3),
    "passes_per_team": (420.0, 60.0, 0.3),
    # cross-validation inside the fit: the stronger side's share of goals, as in the quick sim
    # on the same fixtures (target filled in from the quick sim when the sample is built)
    "strong_goal_share": (0.0, 0.04, 1.0),
    "pass_completion": (0.80, 0.04, 0.3),
    # typical top-flight ball-in-play time (to be sourced, like the passing targets)
    "ball_in_play_min": (55.0, 3.0, 0.5),
    # tactics must not carry the scoring: the default tactic against itself (every club, mirrored)
    # plays a normal match too (spec 008 FR-007, Constitution: no exploit tactics)
    "neutral_goals": (2.48, 0.3, 1.0),
    # open-play crosses a team (typical top-flight value, to be sourced)
    "crosses_per_team": (14.0, 4.0, 0.5),
}
NEUTRAL_SEEDS = 3

TUNABLE = [
    ("attributes.spread", 0.1, 1.0),
    ("decide.shoot_bias", 0.1, 3.0),
    ("decide.min_shot_xg", 0.01, 0.2),
    ("decide.decision_every_s", 0.6, 3.0),
    ("decide.control_delay_s", 0.4, 3.0),
    ("decide.pass_out", 0.02, 0.6),
    ("decide.cross_bias", 0.2, 5.0),
    ("decide.loss_cost", 0.2, 5.0),
    ("decide.lane_pass", 0.6, 0.98),
    ("decide.crowd_pass", 0.6, 0.99),
    ("decide.crowd_discount", 0.1, 3.0),
    ("decide.carry_bias", 0.2, 2.0),
    ("decide.dribble_bias", 0.1, 2.0),
    ("decide.temperature", 0.1, 1.0),
    ("shape.oop_compact", 0.3, 1.0),
    ("shape.oop_push", 0.2, 0.9),
    ("duel.tackle_base", 0.05, 0.6),
    ("duel.foul_base", 0.02, 0.3),
    ("duel.beat_advance", 1.0, 5.0),
    ("xg.block_lane", 0.8, 3.0),
    ("keeper.save_skill", 0.0, 0.05),
    ("home.edge", 0.0, 0.12),
    # the overall strength of the 006 levers (line heights, engagement and tempo are sized by
    # tools/positional_exploit.py: points and openness, not by these targets)
    ("tactics.lever_scale", 0.3, 1.5),
]


_worker: QuickSimProvider | None = None


def _init_worker() -> None:
    global _worker
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    _worker = QuickSimProvider(loaded.dataset)


def _play(n: int, home: str, away: str,
          params: PositionalParams) -> tuple[MatchReport, int, int, float, int]:
    """One fixture on its own seed (so the result does not depend on the process)."""
    assert _worker is not None
    p = _worker
    hs, as_ = p.team_sheet(home), p.team_sheet(away)
    ht, at = p.tactics_for(hs, as_)
    match = LiveMatch(hs, as_, p.dataset.players, params, p.params,
                      random.Random(f"tune:{n}"), False, ht, at, record=False)
    match.play()
    return (match.report(), match.passes, match.passes_completed, match.in_play_s,
            sum(match.crosses.values()))


def _play_neutral(n: int, club: str, params: PositionalParams) -> int:
    """The club against itself, both on the default tactic: total goals."""
    assert _worker is not None
    p = _worker
    sheet = p.team_sheet(club)
    tactic = default_tactic(sheet.formation.name)
    match = LiveMatch(sheet, sheet, p.dataset.players, params, p.params,
                      random.Random(f"neutral:{club}:{n}"), False, tactic, tactic, record=False)
    match.play()
    report = match.report()
    return report.home.goals + report.away.goals


class Sample:
    def __init__(self, fixtures: int) -> None:
        loaded = api.load_dataset(ROOT.parent / "data" / "sample")
        assert loaded.dataset is not None
        self.provider = QuickSimProvider(loaded.dataset)
        clubs = sorted(loaded.dataset.clubs)
        pairs = list(permutations(clubs, 2))
        step = max(1, len(pairs) // fixtures)
        self.pairs = pairs[::step][:fixtures]
        self.strong = {pair: self._stronger(*pair) for pair in self.pairs}
        self.mirrors = [(k, club) for club in clubs for k in range(NEUTRAL_SEEDS)]
        self.pool = ProcessPoolExecutor(min(len(self.pairs), os.cpu_count() or 1),
                                        initializer=_init_worker)
        TARGETS["strong_goal_share"] = (self._quick_strong_share(), 0.04, 1.0)

    def _stronger(self, home: str, away: str) -> str:
        from manager_core.tactics import ai

        players = self.provider.dataset.players
        h = ai.strength(self.provider.team_sheet(home), players)
        a = ai.strength(self.provider.team_sheet(away), players)
        return "home" if h >= a else "away"

    def _quick_strong_share(self) -> float:
        """The stronger side's share of goals in the quick sim, on the same fixtures."""
        from manager_core.quicksim.engine import simulate_match

        p = self.provider
        strong = total = 0
        for n, (h, a) in enumerate(self.pairs):
            hs, as_ = p.team_sheet(h), p.team_sheet(a)
            ht, at = p.tactics_for(hs, as_)
            for k in range(20):
                result, _ = simulate_match(hs, as_, p.dataset.players, p.params,
                                           random.Random(f"xval:{n}:{k}"), False, ht, at)
                goals = (result.home_goals, result.away_goals)
                strong += goals[0] if self.strong[(h, a)] == "home" else goals[1]
                total += sum(goals)
        return strong / total if total else 0.5

    def measure(self, params: PositionalParams) -> dict[str, float]:
        rows = []
        passes = completed = 0
        in_play = 0.0
        strong_goals = all_goals = 0
        homes, aways = zip(*self.pairs, strict=True)
        mirrored = self.pool.map(_play_neutral, *zip(*self.mirrors, strict=True),
                                 [params] * len(self.mirrors))
        played = self.pool.map(_play, range(len(self.pairs)), homes, aways,
                               [params] * len(self.pairs))
        crosses = 0
        for (h, a), (report, made, done, live, crossed) in zip(self.pairs, played, strict=True):
            crosses += crossed
            rows.append(report)
            goals = (report.home.goals, report.away.goals)
            strong_goals += goals[0] if self.strong[(h, a)] == "home" else goals[1]
            all_goals += sum(goals)
            passes += made
            completed += done
            in_play += live
        n = len(rows)

        def mean(f):  # type: ignore[no-untyped-def]
            return statistics.fmean(f(r) for r in rows)

        shots = mean(lambda r: r.home.shots + r.away.shots)
        xg = mean(lambda r: r.home.xg + r.away.xg)
        return {
            "goals": mean(lambda r: r.home.goals + r.away.goals),
            "home_goals": mean(lambda r: r.home.goals),
            "away_goals": mean(lambda r: r.away.goals),
            "shots": shots,
            "on_target_per_side": mean(lambda r: (r.home.shots_on_target
                                                  + r.away.shots_on_target) / 2),
            "xg_per_shot": xg / shots if shots else 0.0,
            "corners": mean(lambda r: r.home.corners + r.away.corners),
            "fouls": mean(lambda r: r.home.fouls + r.away.fouls),
            "yellows": mean(lambda r: r.home.yellows + r.away.yellows),
            "reds": mean(lambda r: r.home.reds + r.away.reds),
            "passes_per_team": passes / n / 2,
            "pass_completion": completed / passes if passes else 0.0,
            "strong_goal_share": strong_goals / all_goals if all_goals else 0.5,
            "ball_in_play_min": in_play / n / 60,
            "neutral_goals": statistics.fmean(mirrored),
            "crosses_per_team": crosses / n / 2,
        }


def loss(values: dict[str, float]) -> float:
    return sum(w * ((values[k] - t) / tol) ** 2 for k, (t, tol, w) in TARGETS.items())


def show(values: dict[str, float]) -> str:
    return " ".join(f"{k}={v:.3g}" for k, v in values.items())


def dump(params: PositionalParams) -> str:
    """The parameters as TOML, keeping the file's group order."""
    lines = [f'model_version = "{params.model_version}"', ""]
    for group, values in params.groups.items():
        lines.append(f"[{group}]")
        lines += [f"{k} = {v!r}" for k, v in values.items()]  # full precision: reproducible
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--fixtures", type=int, default=66)  # strong-side share needs ~160 goals
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    sample = Sample(args.fixtures)
    params = load_params()
    values = sample.measure(params)
    best = loss(values)
    print(f"start loss {best:.3f}  {show(values)}", flush=True)
    step = 1.3
    for round_index in range(args.rounds):
        start = time.time()
        for path, low, high in TUNABLE:
            group, name = path.split(".")
            current = params[group][name]
            for factor in (step, 1 / step):
                value = min(high, max(low, current * factor if current else low))
                if value == current:
                    continue
                trial = params.with_values(**{path: value})
                trial_values = sample.measure(trial)
                score = loss(trial_values)
                if score < best:
                    best, params, values = score, trial, trial_values
                    print(f"  {path} -> {value:.4g}  loss {best:.3f}", flush=True)
                    break
        print(f"round {round_index + 1}: loss {best:.3f} ({time.time() - start:.0f} s)  "
              f"{show(values)}", flush=True)
        step = 1 + (step - 1) * 0.6
        if args.write:  # after every round: a long fit can be stopped without losing it
            MODEL.write_text(dump(params), "utf-8", newline="\n")
            print(f"written to {MODEL}", flush=True)


if __name__ == "__main__":
    main()
