"""Match feed, news and squad view for the terminal UI (spec 005, research R4-R6)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.career import Career
from manager_core.domain.dataset import Dataset
from manager_core.quicksim.report import GOAL_KINDS

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


@pytest.fixture(scope="module")
def played(world: Dataset, tmp_path_factory: pytest.TempPathFactory) -> Career:
    career = api.new_career(world, "feed", "alvorada", master_seed=4)
    api.continue_career(career, tmp_path_factory.mktemp("s"), to_season_end=True)
    return career


def test_feed_replays_every_event_with_the_running_score(played: Career) -> None:
    season = played.season
    for match_id in sorted(season.results)[:40]:
        report = season.results[match_id].report
        assert report is not None
        lines = api.match_feed(season, match_id)
        assert lines[0].kind == "kickoff" and lines[-1].kind == "full_time"
        assert [ln.kind for ln in lines].count("half_time") == 1
        shown = [ln for ln in lines if ln.kind not in ("kickoff", "half_time", "full_time")]
        assert len(shown) == len(report.events)
        home = away = 0
        for line, event in zip(shown, report.events, strict=True):
            assert line.kind == event.kind and line.minute == event.minute
            if event.kind in GOAL_KINDS:
                home += event.side == "home"
                away += event.side == "away"
            assert line.score == (home, away) and line.text
        assert lines[-1].score == (report.home.goals, report.away.goals)


def test_news_covers_the_season(played: Career) -> None:
    news = api.career_news(played)
    kinds = {n.kind for n in news}
    assert {"draw", "result", "champion", "relegated"} <= kinds
    assert [n.day for n in news] == sorted((n.day for n in news), reverse=True)
    user_matches = [m for m in played.season.matches.values()
                    if "alvorada" in (m.home_id, m.away_id) and m.id in played.season.results]
    assert sum(n.kind == "result" for n in news) == len(user_matches)
    assert all(n.text for n in news)


def test_suspensions_appear_in_the_news(played: Career) -> None:
    season = played.season
    bans = 0
    for match_id, result in season.results.items():
        match = season.matches[match_id]
        if "alvorada" not in (match.home_id, match.away_id) or result.report is None:
            continue
        side = "home" if match.home_id == "alvorada" else "away"
        bans += sum(e.kind in ("red", "second_yellow") and e.side == side
                    for e in result.report.events)
    news = [n for n in api.career_news(played) if n.kind == "suspension"]
    assert len(news) >= bans


def test_squad_view(played: Career) -> None:
    rows = api.squad_view(played)
    assert len(rows) == 27
    assert max(r.stars for r in rows) == 5.0 and min(r.stars for r in rows) >= 0.5
    assert all(r.stars * 2 == int(r.stars * 2) for r in rows)
    goals = sum(r.goals for r in rows)
    user_goals = 0
    for match_id, result in played.season.results.items():
        match = played.season.matches[match_id]
        if match.home_id == "alvorada":
            user_goals += sum(e.kind in ("goal", "penalty_goal") and e.side == "home"
                              for e in result.report.events)  # type: ignore[union-attr]
        elif match.away_id == "alvorada":
            user_goals += sum(e.kind in ("goal", "penalty_goal") and e.side == "away"
                              for e in result.report.events)  # type: ignore[union-attr]
    assert goals == user_goals
    assert sum(r.appearances for r in rows) >= 11 * sum(
        1 for m in played.season.matches.values()
        if "alvorada" in (m.home_id, m.away_id) and m.id in played.season.results)
