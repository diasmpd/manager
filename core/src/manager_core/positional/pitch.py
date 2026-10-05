"""Pitch geometry and the xG model (spec 008 research R3).

Team-relative coordinates: `u` runs from a team's own goal line (0) to the opponent's (105), `v`
from its left touchline (0) to its right (68). Absolute coordinates are the home team's view in
the first half; `to_absolute` maps a team's view to them.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

LENGTH = 105.0
WIDTH = 68.0
CENTRE_V = WIDTH / 2
GOAL_HALF = 3.66
PENALTY_SPOT_U = LENGTH - 11.0
BOX_DEPTH = 16.5
BOX_HALF = 20.16


def to_absolute(u: float, v: float, attacks_positive: bool) -> tuple[float, float]:
    return (u, v) if attacks_positive else (LENGTH - u, WIDTH - v)


def goal_geometry(u: float, v: float) -> tuple[float, float]:
    """Distance to the centre of the attacked goal, and the angle the goal mouth subtends."""
    x = LENGTH - u
    y = abs(v - CENTRE_V)
    distance = math.hypot(x, y)
    if x <= 0:
        return distance, 0.0
    denominator = x * x + y * y - GOAL_HALF * GOAL_HALF
    angle = math.atan2(2 * GOAL_HALF * x, denominator)
    return distance, max(0.0, angle)


def xg(
    u: float, v: float, xg_params: Mapping[str, float], header: bool = False, blockers: int = 0
) -> float:
    """Expected goals of a shot from (u, v): a logistic model of distance and angle (public xG
    models' range), lower for headers and for each defender in the shooting lane."""
    distance, angle = goal_geometry(u, v)
    if angle <= 0:
        return 0.0  # on or behind the goal line: no goal mouth to aim at
    logit = xg_params["intercept"] + xg_params["angle"] * angle + xg_params["distance"] * distance
    value = 1 / (1 + math.exp(-logit))
    if header:
        value *= xg_params["header_factor"]
    value *= xg_params["blocker_factor"] ** min(blockers, 2)
    return min(0.95, value)


def in_box(u: float, v: float) -> bool:
    return u >= LENGTH - BOX_DEPTH and abs(v - CENTRE_V) <= BOX_HALF


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_segment_distance(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return distance(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def clamp_point(u: float, v: float) -> tuple[float, float]:
    return min(LENGTH - 0.5, max(0.5, u)), min(WIDTH - 0.5, max(0.5, v))
