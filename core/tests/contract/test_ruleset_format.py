"""Contract: the bundled Mineiro 2026 ruleset (contracts/ruleset-format.md)."""

from datetime import time

from manager_core.competition.rules import (
    DrawMethod,
    EntrantKind,
    GroupStageRule,
    KnockoutStageRule,
    Matching,
    Pairing,
    Tiebreaker,
    TieRule,
    Venue,
    list_rulesets,
    load_ruleset,
)


def test_mineiro_identity_and_validity() -> None:
    r = load_ruleset("mg-modulo-i-2026")
    assert (r.id, r.state, r.country, r.participants) == ("mg-modulo-i-2026", "MG", "BRA", 12)
    assert (r.regulation_year, r.valid_from, r.valid_to) == (2026, 2026, None)
    assert r.is_valid_for(2027) and not r.is_valid_for(2025)


def test_mineiro_scoring_and_tiebreakers() -> None:
    r = load_ruleset("mg-modulo-i-2026")
    assert (r.scoring.win, r.scoring.draw, r.scoring.loss) == (3, 1, 0)
    assert r.scoring.tiebreakers == (
        Tiebreaker.WINS, Tiebreaker.GOAL_DIFFERENCE, Tiebreaker.GOALS_FOR,
        Tiebreaker.HEAD_TO_HEAD, Tiebreaker.FEWER_RED_CARDS, Tiebreaker.FEWER_YELLOW_CARDS,
        Tiebreaker.DRAW,
    )


def test_mineiro_calendar_and_venue() -> None:
    r = load_ruleset("mg-modulo-i-2026")
    c = r.calendar
    assert (c.window_start, c.window_end) == ((1, 8), (3, 8))
    assert c.weekend_days == (5, 6) and c.midweek_days == (2, 3)
    assert (c.kickoff_weekend, c.kickoff_midweek) == (time(16, 0), time(21, 30))
    assert c.min_rest_hours == 66
    assert c.avoid_windows == ("fifa",)
    assert r.neutral_venue is not None
    assert r.neutral_venue.name == "Arena Estadual das Gerais"


def test_mineiro_stages() -> None:
    r = load_ruleset("mg-modulo-i-2026")
    ids = [s.id for s in r.stages]
    assert ids == [
        "primeira-fase", "semifinal", "final", "inconfidencia-semifinal", "inconfidencia-final",
    ]
    first = r.stages[0]
    assert isinstance(first, GroupStageRule)
    assert (first.group_count, first.group_size, first.rounds) == (3, 4, 1)
    assert first.matching is Matching.OTHER_GROUPS
    assert first.draw is DrawMethod.POTS_BY_REPUTATION
    assert [(o.kind, o.places) for o in first.outcomes] == [("relegated", (11, 12))]

    semi, final, inc_semi, inc_final = r.stages[1:]
    assert all(isinstance(s, KnockoutStageRule) for s in (semi, final, inc_semi, inc_final))
    assert isinstance(semi, KnockoutStageRule) and isinstance(final, KnockoutStageRule)
    assert isinstance(inc_semi, KnockoutStageRule) and isinstance(inc_final, KnockoutStageRule)
    assert (semi.track, semi.legs, semi.tie_rule, semi.venue) == (
        "main", 2, TieRule.PENALTIES, Venue.HOME)
    assert semi.pairing is Pairing.CAMPAIGN_1V4_2V3
    assert [e.kind for e in semi.entrants] == [EntrantKind.GROUP_WINNERS, EntrantKind.BEST_OF_PLACE]
    assert (final.legs, final.venue, final.title) == (1, Venue.NEUTRAL, "Campeão Mineiro")
    assert inc_semi.track == "inconfidencia"
    entrant = inc_semi.entrants[0]
    assert (entrant.kind, entrant.places, entrant.exclude_tracks) == (
        EntrantKind.OVERALL_PLACES, (5, 8), ("main",))
    assert inc_semi.tie_rule is TieRule.POINTS_THEN_CAMPAIGN
    assert inc_semi.dates_with == "semifinal"
    assert (inc_final.title, inc_final.legs, inc_final.may_exceed_window) == (
        "Troféu Inconfidência", 2, True)


def test_bundled_rulesets_listed() -> None:
    assert "mg-modulo-i-2026" in [r.id for r in list_rulesets()]
