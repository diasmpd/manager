"""The positional engine's calibration sample and its cross-validation with the quick sim
(spec 008 FR-008 and FR-009, research R6).

The sample is the head of the league sample's fixture list: the same matches, contexts and
random streams the quick sim plays, so the two engines can be compared match for match. It is
played in parallel processes and merged in fixture order (Constitution II).

A positional match costs seconds, so the samples are thinner than the quick sim's: the PR gate
fails only on the robust metrics (`ROBUST`), and the milestone gate on every primary target.
The Mineiro sample's targets are not measured here: its first phase is the same engine on the
same clubs, and the shootout is the model both engines share.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from manager_core.calibration.exploit import _spawnable
from manager_core.calibration.samples import (
    LeagueFixture,
    LeagueMatch,
    league_fixtures,
)
from manager_core.competition.results import MatchContext, Result
from manager_core.domain.dataset import Dataset
from manager_core.positional.params import PositionalParams
from manager_core.quicksim.params import ModelParams
from manager_core.quicksim.provider import QuickSimProvider

MATCHES = {"pr": 300, "milestone": 1500}
# what a thin sample can still judge (research R6): the others only warn at the PR gate
ROBUST = frozenset({
    "goals_per_match", "home_win", "draw", "away_win", "shots_per_match",
    "shots_on_target_per_side", "yellows_per_match", "reds_per_match", "xg_minus_goals",
})
# SC-003: how far the two engines may differ on the same fixtures
CROSS_TOLERANCES = {
    "goals_per_match": 0.15, "home_win": 0.04, "draw": 0.04, "away_win": 0.04,
    "total_goals_0": 0.04, "total_goals_1": 0.04, "total_goals_2": 0.04, "total_goals_3": 0.04,
    "total_goals_4": 0.04, "total_goals_5plus": 0.04,
}
WORKERS = os.cpu_count() or 1
CHUNK = 4  # matches handed to a process at a time


@dataclass(frozen=True, slots=True)
class CrossRow:
    id: str
    positional: float
    quick: float
    tolerance: float

    @property
    def ok(self) -> bool:
        return abs(self.positional - self.quick) <= self.tolerance


@dataclass(frozen=True, slots=True)
class CrossValidation:
    matches: int
    rows: tuple[CrossRow, ...]

    @property
    def passed(self) -> bool:
        return all(row.ok for row in self.rows)

    @property
    def failures(self) -> list[str]:
        return [row.id for row in self.rows if not row.ok]


def fixtures(dataset: Dataset, matches: int) -> list[LeagueFixture]:
    """The first `matches` fixtures of the league sample."""
    clubs = len(dataset.clubs)
    per_season = clubs * (clubs - 1)
    return league_fixtures(dataset, -(-matches // per_season))[:matches]


_worker: QuickSimProvider | None = None


def _init_worker(dataset: Dataset, params: ModelParams, positional: PositionalParams) -> None:
    global _worker
    _worker = QuickSimProvider(dataset, params)
    _worker.positional_params = positional


def _play(fixture: LeagueFixture) -> Result:
    """One fixture on its own random stream (so the result does not depend on the process)."""
    assert _worker is not None
    clubs = _worker.dataset
    match = _worker.live_match(clubs.club(fixture.home_id), clubs.club(fixture.away_id),
                               MatchContext(fixture.seed, "league"), fixture.rng(), record=False)
    match.play()
    return match.result()


def league_sample(dataset: Dataset, params: ModelParams, positional: PositionalParams,
                  matches: int) -> list[LeagueMatch]:
    """The league sample's first `matches` fixtures, played by the positional engine."""
    todo = fixtures(dataset, matches)
    workers = min(WORKERS, len(todo))
    if workers <= 1 or not _spawnable():
        _init_worker(dataset, params, positional)
        results = [_play(f) for f in todo]
    else:
        with ProcessPoolExecutor(workers, initializer=_init_worker,
                                 initargs=(dataset, params, positional)) as pool:
            results = list(pool.map(_play, todo, chunksize=CHUNK))
    return [LeagueMatch(f.season, f.home_id, f.away_id, result)
            for f, result in zip(todo, results, strict=True)]


def cross_validate(positional: Mapping[str, float], quick: Mapping[str, float],
                   matches: int) -> CrossValidation:
    """Both engines' league metrics on the same fixtures, against the SC-003 tolerances."""
    return CrossValidation(matches, tuple(CrossRow(k, positional[k], quick[k], tolerance)
                                          for k, tolerance in CROSS_TOLERANCES.items()))
