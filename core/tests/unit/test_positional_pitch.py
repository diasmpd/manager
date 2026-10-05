"""Pitch geometry, the xG model and the positional record (spec 008 T001, T006)."""

import pytest

from manager_core.positional.params import load_params
from manager_core.positional.pitch import (
    LENGTH,
    PENALTY_SPOT_U,
    WIDTH,
    goal_geometry,
    in_box,
    point_segment_distance,
    to_absolute,
    xg,
)
from manager_core.positional.record import PositionalRecord

XG = load_params()["xg"]


def test_xg_is_in_the_range_of_public_models() -> None:
    """Unopposed open-play shots: penalty spot ~0.2, 16 m ~0.1, 25 m ~0.03, 6 m ~0.5."""
    centre = WIDTH / 2
    assert 0.12 < xg(PENALTY_SPOT_U, centre, XG) < 0.35
    assert 0.06 < xg(LENGTH - 16, centre, XG) < 0.14
    assert 0.01 < xg(LENGTH - 25, centre, XG) < 0.05
    assert 0.35 < xg(LENGTH - 6, centre, XG) < 0.7


def test_xg_falls_with_angle_headers_and_blockers() -> None:
    centre = WIDTH / 2
    assert xg(LENGTH - 12, centre, XG) > xg(LENGTH - 12, centre + 15, XG)
    assert xg(LENGTH - 8, centre, XG, header=True) < xg(LENGTH - 8, centre, XG)
    assert xg(LENGTH - 8, centre, XG, blockers=1) < xg(LENGTH - 8, centre, XG)
    assert xg(LENGTH + 1, centre, XG) < 0.01  # behind the goal line: no angle


def test_geometry() -> None:
    d, angle = goal_geometry(LENGTH - 11, WIDTH / 2)
    assert d == pytest.approx(11)
    assert angle == pytest.approx(0.6432, abs=1e-3)  # 2 * atan(3.66 / 11)
    assert to_absolute(10, 5, attacks_positive=False) == (LENGTH - 10, WIDTH - 5)
    assert in_box(LENGTH - 10, WIDTH / 2) and not in_box(LENGTH - 20, WIDTH / 2)
    assert point_segment_distance((5, 1), (0, 0), (10, 0)) == pytest.approx(1)


def test_record_round_trip() -> None:
    samples = tuple(tuple(range(i, i + 47)) for i in range(10))
    record = PositionalRecord(2.0, (("p1", "home"),), samples, ((3, 0),), ((5, 2, "p9"),))
    assert PositionalRecord.decode(record.encode()) == record
