"""US3: suspensions follow real rules (spec 004 FR-008..FR-010, research R5)."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from manager_core import api
from manager_core.career.discipline import Discipline
from manager_core.competition.season import Match
from manager_core.domain.dataset import Dataset

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def _player(world: Dataset, club: str, n: int = 0) -> str:
    return sorted(m.player_id for m in world.memberships.values() if m.club_id == club)[n]


def _match(n: int, home: str = "alvorada", away: str = "serra-negra") -> Match:
    return Match(f"m{n}", "primeira-fase", n, home, away, datetime(2027, 1, n + 1, 16), "x")


def _result(*events: tuple[str, str, str]) -> SimpleNamespace:
    """events: (side, kind, player id)."""
    return SimpleNamespace(report=SimpleNamespace(events=[
        SimpleNamespace(side=side, kind=kind, player_id=pid) for side, kind, pid in events]))


def test_red_card_is_a_one_match_ban(world: Dataset) -> None:
    d = Discipline(world)
    p = _player(world, "alvorada")
    d.record(_match(1), _result(("home", "red", p)))  # type: ignore[arg-type]
    assert p in d.unavailable(_match(2))
    d.record(_match(2), _result())  # type: ignore[arg-type]
    assert p not in d.unavailable(_match(3))


def test_third_yellow_is_a_ban_and_resets(world: Dataset) -> None:
    d = Discipline(world)
    p = _player(world, "alvorada")
    for n in (1, 2):
        d.record(_match(n), _result(("home", "yellow", p)))  # type: ignore[arg-type]
        assert p not in d.unavailable(_match(n + 1))
    d.record(_match(3), _result(("home", "yellow", p)))  # type: ignore[arg-type]
    assert p in d.unavailable(_match(4))
    assert d.yellows(p) == 0
    d.record(_match(4), _result())  # type: ignore[arg-type]
    assert p not in d.unavailable(_match(5))


def test_second_yellow_counts_toward_the_red_only(world: Dataset) -> None:
    d = Discipline(world)
    p = _player(world, "alvorada")
    d.record(_match(1), _result(("home", "yellow", p)))  # type: ignore[arg-type]
    d.record(_match(2), _result(("home", "yellow", p), ("home", "second_yellow", p)))  # type: ignore[arg-type]
    assert d.yellows(p) == 1  # the second match's yellow became the red
    assert p in d.unavailable(_match(3))


def test_ban_is_served_by_the_players_own_club(world: Dataset) -> None:
    d = Discipline(world)
    p = _player(world, "alvorada")
    d.record(_match(1), _result(("home", "red", p)))  # type: ignore[arg-type]
    other = _match(2, "mineracao", "rio-turvo")
    assert p not in d.unavailable(other)
    d.record(other, _result())  # type: ignore[arg-type]
    assert p in d.unavailable(_match(3, "sertanejo", "alvorada"))  # still to serve


def test_season_suspensions_are_served(world: Dataset) -> None:
    """SC-003 on 10 careers: a sent-off or thrice-booked player misses exactly his club's next
    match; a suspended player never appears in a match."""
    for seed in range(10):
        career = api.new_career(world, "d", "alvorada", master_seed=seed)
        career.season.advance_to(date(2027, 12, 31))
        _check_bans(career.season, world)


@pytest.mark.slow
@pytest.mark.positional
def test_season_suspensions_are_served_with_positional_matches(world: Dataset) -> None:
    """The same on one career whose own matches are played by the positional engine (spec 008):
    its cards feed the same bans."""
    career = api.new_career(world, "d", "alvorada", master_seed=3)
    assert career.positional
    career.season.advance_to(date(2027, 12, 31))
    sources = {r.source for r in career.season.results.values()}
    assert "positional" in sources and len(sources) == 2
    _check_bans(career.season, world)


@pytest.mark.slow
def test_season_suspensions_are_served_100(world: Dataset) -> None:
    for seed in range(10, 100):
        career = api.new_career(world, "d", "alvorada", master_seed=seed)
        career.season.advance_to(date(2027, 12, 31))
        _check_bans(career.season, world)


def _check_bans(season: object, world: Dataset) -> None:
    matches = sorted((m for m in season.matches.values() if m.id in season.results),  # type: ignore[attr-defined]
                     key=lambda m: (m.kickoff, m.id))
    club_of = {pid: m.club_id for pid, m in world.memberships.items()}
    yellows: dict[str, int] = {}
    owed: dict[str, int] = {}
    for m in matches:
        report = season.results[m.id].report  # type: ignore[attr-defined]
        involved = {pid for side in ("home", "away") for lineup in [report.lineup(side)]
                    for pid in [p for _, p in lineup.starters] + list(lineup.bench)}
        for pid, n in list(owed.items()):
            if n and club_of[pid] in (m.home_id, m.away_id):
                assert pid not in involved, (m.id, pid)
                owed[pid] = n - 1
        sent = {e.player_id for e in report.events if e.kind in ("red", "second_yellow")}
        for e in report.events:
            if e.kind == "yellow" and e.player_id not in sent:
                yellows[e.player_id] = yellows.get(e.player_id, 0) + 1
                if yellows[e.player_id] == 3:
                    yellows[e.player_id] = 0
                    owed[e.player_id] = owed.get(e.player_id, 0) + 1
        for pid in sent:
            owed[pid] = owed.get(pid, 0) + 1
