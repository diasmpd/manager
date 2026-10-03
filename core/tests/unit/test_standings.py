"""Tables and tiebreakers (FR-012..014, research R8, SC-004)."""

import tomllib
from pathlib import Path

import pytest

from manager_core.competition.results import Result
from manager_core.competition.rules import load_ruleset
from manager_core.competition.standings import PlayedMatch, build_table

SCENARIOS = sorted((Path(__file__).resolve().parents[1] / "fixtures" / "tiebreaks").glob("*.toml"))
SCORING = load_ruleset("mg-modulo-i-2026").scoring


def _played(raw: list[list[object]]) -> list[PlayedMatch]:
    matches = []
    for m in raw:
        h, a, hg, ag = str(m[0]), str(m[1]), int(m[2]), int(m[3])  # type: ignore[call-overload]
        cards = [int(v) for v in m[4:8]] if len(m) == 8 else [None] * 4  # type: ignore[call-overload]
        result = Result(hg, ag, "test", home_red=cards[0], away_red=cards[1],
                        home_yellow=cards[2], away_yellow=cards[3])
        matches.append(PlayedMatch(h, a, result))
    return matches


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario(path: Path) -> None:
    sc = tomllib.loads(path.read_text("utf-8"))
    rows = build_table(sc["clubs"], _played(sc["matches"]), SCORING, seed=1, label=path.stem)
    order = [r.club_id for r in rows]
    if "expect_order" in sc:
        positions = [order.index(c) for c in sc["expect_order"]]
        assert positions == sorted(positions), order
    for club, criterion in sc.get("expect_decided_by", {}).items():
        row = next(r for r in rows if r.club_id == club)
        assert row.decided_by == criterion, (club, [(r.club_id, r.decided_by) for r in rows])
    for club, criterion in sc.get("expect_decided_by_any", {}).items():
        row_index = order.index(club)
        # the separation between a and b (whichever is above) must be by lots
        other = "b" if club == "a" else "a"
        upper = min(row_index, order.index(other))
        assert rows[upper].decided_by == criterion, [(r.club_id, r.decided_by) for r in rows]


def test_at_least_ten_scenarios() -> None:
    assert len(SCENARIOS) >= 10


def test_lots_are_deterministic() -> None:
    sc = tomllib.loads((SCENARIOS[0].parent / "s08_full_tie_lots.toml").read_text("utf-8"))
    first = build_table(sc["clubs"], _played(sc["matches"]), SCORING, seed=7, label="x")
    for _ in range(20):
        assert build_table(sc["clubs"], _played(sc["matches"]), SCORING, seed=7, label="x") == first


def test_columns_are_consistent() -> None:
    sc = tomllib.loads(SCENARIOS[1].read_text("utf-8"))
    rows = build_table(sc["clubs"], _played(sc["matches"]), SCORING, seed=1, label="x")
    for r in rows:
        assert r.played == r.won + r.drawn + r.lost
        assert r.goal_difference == r.goals_for - r.goals_against
        assert r.points == 3 * r.won + r.drawn
    assert [r.place for r in rows] == list(range(1, len(rows) + 1))
    assert rows[-1].decided_by is None
