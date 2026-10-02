from collections import Counter

import pytest

from manager import Match, Player, Position, Tactic, make_team
from manager.engine import MAX_SUBS, PlayerState, caution_level


def play(n, home_q=11, away_q=11, home_tactic=None, away_tactic=None):
    for i in range(n):
        home = make_team("Casa", quality=home_q, seed=i * 2)
        away = make_team("Fora", quality=away_q, seed=i * 2 + 1)
        if home_tactic:
            home.tactic = home_tactic
        if away_tactic:
            away.tactic = away_tactic
        m = Match(home, away, seed=i)
        m.simulate()
        yield m


def test_same_seed_replays_same_match():
    a = Match(make_team("A", seed=1), make_team("B", seed=2), seed=42).simulate()
    b = Match(make_team("A", seed=1), make_team("B", seed=2), seed=42).simulate()
    assert [e.text for e in a] == [e.text for e in b]


def test_goal_average_is_realistic():
    goals = sum(sum(m.score) for m in play(400))
    assert 2.0 <= goals / 400 <= 2.8


def test_stronger_team_wins_most_games():
    results = Counter()
    for m in play(300, home_q=14, away_q=9):
        h, a = m.score
        results["win" if h > a else "other"] += 1
    assert results["win"] / 300 > 0.65


def test_unbooked_player_is_not_cautious():
    ps = PlayerState(Player("X", Position.DF, composure=20))
    assert caution_level(ps, True) == 0.0


def test_composed_players_adapt_more_than_hotheads():
    calm = PlayerState(Player("Calmo", Position.DF, composure=18, aggression=6), yellow=True)
    hothead = PlayerState(Player("Esquentado", Position.DF, composure=4, aggression=18), yellow=True)
    assert caution_level(calm, True) > caution_level(hothead, True)


def test_caution_disabled_by_tactic():
    ps = PlayerState(Player("X", Position.DF, composure=20), yellow=True)
    assert caution_level(ps, False) == 0.0


def test_card_caution_reduces_second_yellows():
    def second_yellows(caution: bool) -> int:
        tactic = lambda: Tactic(card_caution=caution)
        return sum(
            sum(e.kind == "second_yellow" for e in m.events)
            for m in play(600, home_tactic=tactic(), away_tactic=tactic())
        )
    with_caution, without = second_yellows(True), second_yellows(False)
    assert with_caution < without * 0.7, (with_caution, without)


def test_caution_has_a_cost_booked_defenders_lose_more_duels():
    """Holding back must not be free: cautious booked players should lose a bigger share of duels."""
    def booked_duel_loss_rate(caution: bool) -> float:
        won = lost = 0
        tactic = lambda: Tactic(card_caution=caution)
        for i in range(400):
            m = Match(make_team("A", seed=i * 2), make_team("B", seed=i * 2 + 1), seed=i)
            m.home.team.tactic, m.away.team.tactic = tactic(), tactic()
            # Book every starter from kick-off so the effect is measurable.
            for ts in (m.home, m.away):
                for ps in ts.lineup:
                    ps.yellow = True
            m.simulate()
            for ts in (m.home, m.away):
                for ps in ts.lineup:
                    won += ps.tackles_won
                    lost += ps.tackles_lost
        return lost / (won + lost)
    assert booked_duel_loss_rate(True) > booked_duel_loss_rate(False)


def test_substitution_swaps_player_and_enforces_limit():
    home = make_team("A", seed=1)
    m = Match(home, make_team("B", seed=2), seed=1)
    starter, sub = home.starters[5].name, home.bench[0].name
    m.substitute("home", starter, sub)
    names = [p.player.name for p in m.home.on_pitch()]
    assert sub in names and starter not in names
    with pytest.raises(ValueError):
        m.substitute("home", starter, home.bench[1].name)  # already off
    for i in range(1, MAX_SUBS):
        m.substitute("home", home.starters[i].name, home.bench[i].name)
    with pytest.raises(ValueError):
        m.substitute("home", home.starters[10].name, home.bench[6].name)


def test_sent_off_player_leaves_the_pitch():
    for m in play(200):
        for ts in (m.home, m.away):
            off = [p for p in ts.all_states if p.sent_off]
            assert len(ts.on_pitch()) == 11 - len(off)
            assert all(not p.on_pitch for p in off)
