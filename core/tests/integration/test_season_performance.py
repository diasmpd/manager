"""SC-005: start and play a full season in under 2 s on the reference PC."""

import os
import time
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import PlaceholderProvider


@pytest.mark.slow
def test_full_season_is_fast(sample_dir: Path) -> None:
    dataset = api.load_dataset(sample_dir).dataset
    assert dataset is not None
    limit = float(os.environ.get("MANAGER_PERF_LIMIT_S", "2.0"))
    timings = []
    for seed in range(3):  # best of 3: robust to a busy machine
        start = time.perf_counter()
        season = api.start_season(dataset, "mg-modulo-i-2026", 2027, seed,
        result_provider=PlaceholderProvider(dataset))
        api.advance_to(season, date(2027, 12, 31))
        timings.append(time.perf_counter() - start)
        assert api.season_outcomes(season) is not None
    assert min(timings) < limit, timings
