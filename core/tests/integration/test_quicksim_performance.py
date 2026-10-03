"""Quick-sim performance budgets (SC-004). Limits scale with MANAGER_PERF_LIMIT_S / 2 (CI runners
are slower than the reference PC)."""

import os
import random
import time
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.provider import _SHEET_CACHE, QuickSimProvider

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
SCALE = float(os.environ.get("MANAGER_PERF_LIMIT_S", "2.0")) / 2.0

pytestmark = pytest.mark.slow


def test_full_season_from_a_cold_provider() -> None:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    _SHEET_CACHE.clear()
    start = time.perf_counter()
    season = api.start_season(loaded.dataset, "mg-modulo-i-2026", 2027, 1)
    api.advance_to(season, date(2027, 12, 31))
    assert time.perf_counter() - start < 3.0 * SCALE


def test_matchdays() -> None:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    provider = QuickSimProvider(loaded.dataset)
    clubs = sorted(loaded.dataset.clubs)
    for club in clubs:
        provider.team_sheet(club)

    def matchday(pairs: list[tuple[str, str]]) -> float:
        start = time.perf_counter()
        for n, (home, away) in enumerate(pairs):
            simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                           loaded.dataset.players, provider.params, random.Random(n))
        return time.perf_counter() - start

    mineiro = [(clubs[i], clubs[i + 6]) for i in range(6)]
    league = [(clubs[i % 12], clubs[(i + 5) % 12]) for i in range(10)]
    assert matchday(mineiro) < 0.5 * SCALE
    assert matchday(league) < 1.0 * SCALE
