"""Calibration targets as data (FR-017, contracts/calibration-targets.md)."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

from manager_core.i18n import t

METRIC_IDS = (
    "goals_per_match", "home_win", "draw", "away_win", "home_goals", "away_goals", "nil_nil",
    "total_goals_0", "total_goals_1", "total_goals_2", "total_goals_3", "total_goals_4",
    "total_goals_5plus", "fav_win", "fav_draw", "fav_loss", "yellows_per_match",
    "reds_per_match", "mineiro_draw", "mineiro_goals_per_match", "shots_per_match",
    "shots_on_target_per_side", "xg_minus_goals", "corners_per_match", "fouls_per_match",
    "late_goal_share", "first_half_goal_share", "shootout_conversion", "own_goal_share",
)
SAMPLES = ("league", "mineiro")
KINDS = ("primary", "secondary")
UNITS = ("per_match", "per_side", "ratio")
TARGETS_ENV = "MANAGER_CALIBRATION_TARGETS"  # test hook: an alternative targets file


@dataclass(frozen=True, slots=True)
class CalibrationTarget:
    id: str
    sample: str
    kind: str
    unit: str
    target: float
    low: float
    high: float
    source: str
    retrieved: date

    @property
    def primary(self) -> bool:
        return self.kind == "primary"

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


class TargetsError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems  # key paths
        super().__init__("; ".join(t("calibration.C001", path=p) for p in problems))


def _parse(doc: dict[str, Any]) -> tuple[CalibrationTarget, ...]:
    problems: list[str] = []
    targets: list[CalibrationTarget] = []
    seen: set[str] = set()
    for i, raw in enumerate(doc.get("targets", [])):
        path = f"targets[{i}]"
        try:
            target = CalibrationTarget(
                id=raw["id"], sample=raw["sample"], kind=raw["kind"], unit=raw["unit"],
                target=float(raw["target"]), low=float(raw["low"]), high=float(raw["high"]),
                source=raw["source"], retrieved=raw["retrieved"],
            )
        except (KeyError, TypeError, ValueError):
            problems.append(path)
            continue
        if target.id not in METRIC_IDS or target.id in seen:
            problems.append(f"{path}.id")
        if (target.sample not in SAMPLES or target.kind not in KINDS
                or target.unit not in UNITS):
            problems.append(path)
        if not target.low <= target.target <= target.high:
            problems.append(f"{path}.target")
        if not isinstance(target.retrieved, date) or not target.source:
            problems.append(f"{path}.source")
        seen.add(target.id)
        targets.append(target)
    if not targets and not problems:
        problems.append("targets")
    if problems:
        raise TargetsError(problems)
    return tuple(targets)


def load_targets_file(path: Path) -> tuple[CalibrationTarget, ...]:
    return _parse(tomllib.loads(path.read_text("utf-8")))


def load_targets() -> tuple[CalibrationTarget, ...]:
    override = os.environ.get(TARGETS_ENV)
    if override:
        return load_targets_file(Path(override))
    entry = (resources.files("manager_core.reference").joinpath("calibration")
             .joinpath("quicksim-targets.toml"))
    return _parse(tomllib.loads(entry.read_text("utf-8")))
