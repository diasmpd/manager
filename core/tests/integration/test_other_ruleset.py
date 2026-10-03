"""US3: a structurally different ruleset plays to the end with no code changes (FR-001)."""

import re
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.results import Result
from manager_core.competition.season import Season
from manager_core.competition.standings import PlayedMatch, build_table
from manager_core.domain.dataset import Dataset

RULESET = "test-liga-unica"
SRC = Path(__file__).resolve().parents[2] / "src" / "manager_core"


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    loaded = api.load_dataset(Path(__file__).resolve().parents[3] / "data" / "sample")
    assert loaded.dataset is not None
    return loaded.dataset


def _played(dataset: Dataset, master_seed: int) -> Season:
    participants = sorted(dataset.clubs)[:8]
    season = api.start_season(dataset, RULESET, 2027, master_seed, participants)
    api.advance_to(season, date(2027, 12, 31))
    return season


@pytest.mark.parametrize("master_seed", range(30))
def test_liga_unica_plays_to_the_end(dataset: Dataset, master_seed: int) -> None:
    season = _played(dataset, master_seed)
    out = api.season_outcomes(season)
    assert out is not None
    league = [m for m in season.matches.values() if m.stage_id == "turno-returno"]
    assert len(league) == 8 * 7  # double round-robin
    assert {m.round for m in league} == set(range(1, 15))
    pairs = {(m.home_id, m.away_id) for m in league}
    assert len(pairs) == 56  # every pair once at home, once away
    overall = [r.club_id for r in api.season_table(season)]
    assert set(out.main_entrants) == set(overall[:2])  # the final is 1st v 2nd
    assert out.relegated == [overall[7]]
    assert {out.champion, out.runner_up} == set(overall[:2])
    final = api.season_bracket(season)
    assert len(final) == 1 and len(final[0].legs) == 2
    assert final[0].decided_by in ("points", "campaign")  # no penalties in this format
    assert all(leg.result is not None and leg.result.shootout is None for leg in final[0].legs)
    assert all(leg.home_id != leg.venue for leg in final[0].legs)
    assert final[0].legs[1].home_id == overall[0]  # better campaign hosts the second leg
    end = date(2027, 4, 30)
    assert all(m.kickoff.date() <= end for m in season.matches.values())


def test_goal_difference_is_ranked_before_wins(dataset: Dataset) -> None:
    rules = api.load_ruleset(RULESET)
    # a: 2 wins 1 loss (6 pts, GD +1); b: 1 win 3 draws (6 pts, GD +4)
    r = lambda h, a: Result(h, a, "test")  # noqa: E731
    matches = [PlayedMatch("a", "x", r(1, 0)), PlayedMatch("a", "y", r(1, 0)),
               PlayedMatch("a", "z", r(0, 1)),
               PlayedMatch("b", "x", r(4, 0)), PlayedMatch("b", "y", r(0, 0)),
               PlayedMatch("b", "z", r(0, 0)), PlayedMatch("b", "w", r(0, 0))]
    rows = build_table(("a", "b"), matches, rules.scoring, 1, "gd-first")
    assert [row.club_id for row in rows] == ["b", "a"]
    assert rows[0].decided_by == "goal_difference"


def test_replay_is_identical(dataset: Dataset) -> None:
    a, b = _played(dataset, 7), _played(dataset, 7)
    assert a.results == b.results and a.outcome() == b.outcome()


def test_engine_has_no_ruleset_specific_code() -> None:
    """Rulesets are data: the engine, facade and CLI never test for a ruleset, stage or track
    of a specific competition."""
    specific = re.compile(r"mg-modulo|inconfid|primeira-fase|semifinal\"|mineir|liga-unica",
                          re.IGNORECASE)
    for path in [*(SRC / "competition").glob("*.py"), SRC / "api.py", SRC / "cli.py"]:
        for n, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            code = line.split("#", 1)[0]
            if code.startswith("DEFAULT_RULESET = "):  # the documented CLI default
                continue
            assert not specific.search(code), f"{path.name}:{n}: {line.strip()}"
