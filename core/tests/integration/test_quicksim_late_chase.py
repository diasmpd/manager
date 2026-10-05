"""Late game state (spec 003 US3, research R4/R5): late on, a side one goal down scores more
than a level side, and so does the side one goal up (its opponent is exposed). Lago et al. give
the directions; the sizes are not calibrated anywhere.

Statistics (spec 006 research R6): a 6,000-match sample has a standard error of about 0.05 on
these ratios, so a single small sample with tight thresholds is a coin flip. This pools 24,000
mirrored matches (SE about 0.025) and checks the directions with a margin.
"""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.calibration.metrics import late_goal_rates
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.provider import QuickSimProvider

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MATCHES = 24_000


@pytest.fixture(scope="module")
def ratios() -> dict[int, float]:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    provider = QuickSimProvider(loaded.dataset, ai_styles=False)
    sheet = provider.team_sheet("mineracao")  # a club against itself, at a neutral venue
    reports = (simulate_match(sheet, sheet, provider.dataset.players, provider.params,
                              random.Random(f"mirror:{n}"), neutral=True)[1]
               for n in range(MATCHES))
    rates = late_goal_rates(reports)
    return {d: rates[d] / rates[0] for d in (-1, 1)}


def test_a_trailing_side_pushes(ratios: dict[int, float]) -> None:
    assert ratios[-1] > 1.04, ratios


def test_a_leading_side_scores_into_the_space(ratios: dict[int, float]) -> None:
    assert ratios[1] > 1.00, ratios
