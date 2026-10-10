"""Players behave like players (spec 008 US4, FR-007, SC-006): one statistical test per
behaviour, on common seeds, each with the trade-off the constitution asks for (V).

Duel behaviours are measured on isolated challenges (thousands, cheap); the others on matches,
where a comparison forks one match at a minute so both arms share everything before it.
"""

import copy
import dataclasses
import random
import statistics
from collections.abc import Callable
from pathlib import Path

import pytest

from manager_core import api
from manager_core.positional.engine import Body, LiveMatch
from manager_core.positional.params import load_params
from manager_core.quicksim.engine import caution_strength
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.ratings import Group
from manager_core.tactics.model import Tactic, default_tactic

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
HOME, AWAY = "mineracao", "rio-turvo"
CHALLENGES = 20000


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset, ai_styles=False)


def _match(provider: QuickSimProvider, seed: int, home_tactic: Tactic | None = None,
           swap: bool = False) -> LiveMatch:
    home, away = (AWAY, HOME) if swap else (HOME, AWAY)
    return LiveMatch(provider.team_sheet(home), provider.team_sheet(away),
                     provider.dataset.players, load_params(), provider.params,
                     random.Random(seed), False, home_tactic, record=False)


def _fork(match: LiveMatch) -> LiveMatch:
    """A copy that plays on by itself (the reference data is shared, not copied)."""
    shared = (match.players, match.p, match.q, *match.players.values(),
              *(team.sheet for team in match.teams.values()))
    return copy.deepcopy(match, {id(x): x for x in shared})


def _play_to(match: LiveMatch, minute: int) -> None:
    while (match.half == 1 or match.minute().base < minute) and not match.finished:
        match.advance(30)


def _challenges(provider: QuickSimProvider, pick: Callable[[list[Body]], Body],
                arm: Callable[[LiveMatch, Body], None], swap: bool = False) -> tuple[int, int]:
    """`CHALLENGES` isolated challenges by one away defender on a home midfielder, each from
    the same state: (fouls he commits, balls he wins). `swap` exchanges the clubs."""
    match = _match(provider, 1, swap=swap)
    home, away = match.teams["home"], match.teams["away"]
    carrier = next(b for b in home.on_pitch() if b.group is Group.MIDFIELDER)
    defender = pick([b for b in away.on_pitch() if b.group in (Group.DEFENDER, Group.MIDFIELDER)])
    for body in away.on_pitch():
        if body is not defender:
            body.x, body.y = 90.0, 5.0  # out of the way
    fouls = won = 0
    for _ in range(CHALLENGES):
        defender.on, defender.yellow, defender.energy = True, False, 1.0
        arm(match, defender)
        carrier.x, carrier.y = 52.0, 34.0
        defender.x, defender.y = 53.0, 34.0
        match._challenged.clear()
        match._duel_clock = 99.0
        match.dead_until = 0.0
        match._give(carrier)
        before = away.fouls
        match._duels(0.25)
        fouls += away.fouls - before
        won += match.ball.owner is defender
    return fouls, won


def _plain(match: LiveMatch, defender: Body) -> None:
    pass


def _booked(match: LiveMatch, defender: Body) -> None:
    defender.yellow = True


def _calmest(provider: QuickSimProvider) -> Callable[[list[Body]], Body]:
    return lambda bodies: max(bodies, key=lambda b: (caution_strength(b.player, provider.params),
                                                     b.pid))


def test_a_booked_player_fouls_less_and_wins_the_ball_less(provider: QuickSimProvider) -> None:
    """Card caution (the owner's pain point): the calm, smart player eases off, at a cost."""
    fouls, won = _challenges(provider, _calmest(provider), _plain)
    booked_fouls, booked_won = _challenges(provider, _calmest(provider), _booked)
    assert booked_fouls < 0.75 * fouls
    assert booked_won < 0.96 * won


def test_a_booked_hot_head_does_not_change(provider: QuickSimProvider) -> None:
    """Temperament and decisions drive the caution (spec 003): at the bottom there is none."""
    def hot_head(bodies: list[Body]) -> Body:
        return min(bodies, key=lambda b: (caution_strength(b.player, provider.params), b.pid))

    chosen = hot_head(_match(provider, 1, swap=True).teams["away"].on_pitch())
    assert caution_strength(chosen.player, provider.params) == 0
    plain = _challenges(provider, hot_head, _plain, swap=True)
    assert plain[0] > 0 and plain[1] > 0
    assert _challenges(provider, hot_head, _booked, swap=True) == plain


def test_a_tired_player_loses_more_duels(provider: QuickSimProvider) -> None:
    def tired(match: LiveMatch, defender: Body) -> None:
        defender.energy = 0.1

    _, won = _challenges(provider, _calmest(provider), _plain)
    _, tired_won = _challenges(provider, _calmest(provider), tired)
    assert tired_won < 0.85 * won


def test_a_side_two_goals_up_defends_less_tightly(provider: QuickSimProvider) -> None:
    """The relaxed leader (research R5)."""
    def two_up(match: LiveMatch, defender: Body) -> None:
        match.teams["away"].goals = 2

    _, won = _challenges(provider, _calmest(provider), _plain)
    _, relaxed_won = _challenges(provider, _calmest(provider), two_up)
    assert relaxed_won < 0.9 * won


@pytest.mark.slow
def test_distances_are_realistic_and_tired_legs_sprint_less(provider: QuickSimProvider) -> None:
    """Outfield players who play the whole match cover a professional's distance, and the share
    of it they sprint is lower in the last half hour than in the first (they save their legs
    for the runs that matter)."""
    early_m = early_sprint = late_m = late_sprint = 0.0
    for seed in (1, 2):
        match = _match(provider, seed)

        def snapshot(match: LiveMatch = match) -> dict[str, tuple[float, float]]:
            return {b.pid: (b.distance, b.sprint)
                    for team in match.teams.values() for b in team.bodies}

        while match.half == 1 and match.minute().base <= 30:
            match.advance(30)
        at_30 = snapshot()
        _play_to(match, 61)
        at_60 = snapshot()
        match.play()
        end = snapshot()
        came_on = {e.other_player_id for e in match.events if e.kind == "sub"}
        whole = [b for team in match.teams.values() for b in team.on_pitch()
                 if b.group is not Group.GOALKEEPER and b.pid not in came_on]
        assert len(whole) >= 8
        for body in whole:
            assert 8_000 <= end[body.pid][0] <= 14_000, (body.pid, end[body.pid][0])
            early_m += at_30[body.pid][0]
            early_sprint += at_30[body.pid][1]
            late_m += end[body.pid][0] - at_60[body.pid][0]
            late_sprint += end[body.pid][1] - at_60[body.pid][1]
    assert late_sprint / late_m < 0.95 * (early_sprint / early_m)


@pytest.mark.slow
def test_late_on_the_trailing_side_attacks_and_the_leading_side_drops(
    provider: QuickSimProvider,
) -> None:
    """Game state: from minute 70 the same match is played on level and with the home side a
    goal down. Trailing, the home side shoots more; leading, the away side defends deeper."""
    shots = {"level": 0, "trailing": 0}
    lines: dict[str, list[float]] = {"level": [], "trailing": []}
    for seed in range(4):
        match = _match(provider, seed)
        _play_to(match, 70)
        for arm, away_goals in (("level", 0), ("trailing", 1)):
            fork = _fork(match)
            home, away = fork.teams["home"], fork.teams["away"]
            home.goals, away.goals = 0, away_goals
            before = home.shots
            while not fork.finished:
                fork.advance(10)
                owner = fork.ball.owner
                if owner is not None and owner.side == "home":
                    lines[arm].append(statistics.fmean(
                        fork.rel("away", b.x, b.y)[0] for b in away.on_pitch()
                        if b.group is Group.DEFENDER))
            shots[arm] += home.shots - before
    assert shots["trailing"] > 1.2 * shots["level"]
    assert statistics.fmean(lines["trailing"]) < statistics.fmean(lines["level"]) - 2.0


def _with_team(tactic: Tactic, **settings: str) -> Tactic:
    team = dict(tactic.team)
    team.update(settings)
    return dataclasses.replace(tactic, team=tuple(sorted(team.items())))


def _shape(provider: QuickSimProvider, **settings: str) -> tuple[float, float]:
    """The home side's first 15 minutes on three seeds: (its defenders' average height without
    the ball, its outfield players' average spread across the pitch with it), in metres."""
    tactic = _with_team(default_tactic(provider.team_sheet(HOME).formation.name), **settings)
    heights, spreads = [], []
    for seed in range(3):
        match = _match(provider, seed, tactic)
        home = match.teams["home"]
        while match.half == 1 and match.minute().base <= 15:
            match.advance(5)
            owner = match.ball.owner
            if owner is None:
                continue
            outfield = [b for b in home.on_pitch() if b.group is not Group.GOALKEEPER]
            if owner.side == "home":
                across = [match.rel("home", b.x, b.y)[1] for b in outfield]
                spreads.append(max(across) - min(across))
            else:
                heights.append(statistics.fmean(match.rel("home", b.x, b.y)[0] for b in outfield
                                                if b.group is Group.DEFENDER))
    return statistics.fmean(heights), statistics.fmean(spreads)


def test_a_higher_defensive_line_plays_higher_up_the_pitch(provider: QuickSimProvider) -> None:
    deep, _ = _shape(provider, defensive_line="deeper")
    high, _ = _shape(provider, defensive_line="much_higher")
    assert high > deep + 2.0


def test_a_wider_attack_spreads_the_team(provider: QuickSimProvider) -> None:
    _, narrow = _shape(provider, attacking_width="much_narrower")
    _, wide = _shape(provider, attacking_width="much_wider")
    assert wide > narrow + 4.0
