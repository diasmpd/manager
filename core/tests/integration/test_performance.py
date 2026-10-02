"""SC-001: the sample world loads and validates in under 2 s on the reference PC.
Shared CI runners are slower and noisier, so CI sets MANAGER_PERF_LIMIT_S=4.0."""

import os
import time
from pathlib import Path

import pytest

from manager_core import api


@pytest.mark.slow
def test_sample_loads_quickly(sample_dir: Path) -> None:
    limit = float(os.environ.get("MANAGER_PERF_LIMIT_S", "2.0"))
    start = time.perf_counter()
    result = api.load_dataset(sample_dir)
    elapsed = time.perf_counter() - start
    assert result.dataset is not None
    assert elapsed < limit, f"{elapsed:.2f}s >= {limit}s"
