"""Calibration metrics by id (contracts/calibration-targets.md)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from manager_core.calibration.samples import LeagueMatch
from manager_core.competition.rules import load_ruleset
from manager_core.competition.season import Season
from manager_core.competition.seeds import sub_seed
from manager_core.competition.standings import PlayedMatch, build_table
from manager_core.quicksim.report import GOAL_KINDS, MatchReport, Minute

FAVOURITE_SHARE = 3  # top 3 v bottom 3 of 12 (= top 5 v bottom 5 of 20)


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def league_metrics(matches: Sequence[LeagueMatch]) -> dict[str, float]:
    n = len(matches)
    results = [m.result for m in matches]
    totals = [r.home_goals + r.away_goals for r in results]
    reports: list[MatchReport] = [r.report for r in results if r.report is not None]
    m: dict[str, float] = {
        "goals_per_match": _ratio(sum(totals), n),
        "home_win": _ratio(sum(r.home_goals > r.away_goals for r in results), n),
        "draw": _ratio(sum(r.home_goals == r.away_goals for r in results), n),
        "away_win": _ratio(sum(r.home_goals < r.away_goals for r in results), n),
        "home_goals": _ratio(sum(r.home_goals for r in results), n),
        "away_goals": _ratio(sum(r.away_goals for r in results), n),
        "nil_nil": _ratio(sum(t == 0 for t in totals), n),
        "yellows_per_match": _ratio(sum((r.home_yellow or 0) + (r.away_yellow or 0)
                                        for r in results), n),
        "reds_per_match": _ratio(sum((r.home_red or 0) + (r.away_red or 0) for r in results), n),
    }
    for k in range(5):
        m[f"total_goals_{k}"] = _ratio(sum(t == k for t in totals), n)
    m["total_goals_5plus"] = _ratio(sum(t >= 5 for t in totals), n)
    m.update(_favourites(matches))
    if reports:
        r_n = len(reports)
        m["shots_per_match"] = _ratio(sum(x.home.shots + x.away.shots for x in reports), r_n)
        m["shots_on_target_per_side"] = _ratio(
            sum(x.home.shots_on_target + x.away.shots_on_target for x in reports), 2 * r_n)
        m["xg_minus_goals"] = _ratio(sum(x.home.xg + x.away.xg - x.home.goals - x.away.goals
                                         for x in reports), r_n)
        m["corners_per_match"] = _ratio(sum(x.home.corners + x.away.corners for x in reports),
                                        r_n)
        m["fouls_per_match"] = _ratio(sum(x.home.fouls + x.away.fouls for x in reports), r_n)
        goals = [e for x in reports for e in x.events if e.kind in GOAL_KINDS]
        m["late_goal_share"] = _ratio(sum(e.minute.base > 75 for e in goals), len(goals))
        m["first_half_goal_share"] = _ratio(sum(e.minute.base <= 45 for e in goals), len(goals))
        m["own_goal_share"] = _ratio(sum(e.kind == "own_goal" for e in goals), len(goals))
    return m


def _favourites(matches: Sequence[LeagueMatch]) -> dict[str, float]:
    """Favourite results in top-3 v bottom-3 matches, ranked by each season's final table."""
    scoring = load_ruleset("mg-modulo-i-2026").scoring
    win = draw = loss = 0
    for season in sorted({m.season for m in matches}):
        played = [m for m in matches if m.season == season]
        clubs = sorted({m.home_id for m in played})
        table = build_table(clubs, [PlayedMatch(m.home_id, m.away_id, m.result) for m in played],
                            scoring, sub_seed(0, f"calibration:{season}"), "calibration")
        order = [row.club_id for row in table]
        top, bottom = set(order[:FAVOURITE_SHARE]), set(order[-FAVOURITE_SHARE:])
        for m in played:
            if m.home_id in top and m.away_id in bottom:
                fav, dog = m.result.home_goals, m.result.away_goals
            elif m.away_id in top and m.home_id in bottom:
                fav, dog = m.result.away_goals, m.result.home_goals
            else:
                continue
            win += fav > dog
            draw += fav == dog
            loss += fav < dog
    total = win + draw + loss
    return {"fav_win": _ratio(win, total), "fav_draw": _ratio(draw, total),
            "fav_loss": _ratio(loss, total)}


def mineiro_metrics(seasons: Sequence[Season]) -> dict[str, float]:
    first_phase = [s.results[m.id] for s in seasons for m in s.matches.values()
                   if m.stage_id == s.ruleset.group_stage.id]
    n = len(first_phase)
    kicks = [k for s in seasons for r in s.results.values() if r.shootout is not None
             for k in r.shootout.kicks]
    return {
        "mineiro_draw": _ratio(sum(r.home_goals == r.away_goals for r in first_phase), n),
        "mineiro_goals_per_match": _ratio(sum(r.home_goals + r.away_goals for r in first_phase),
                                          n),
        "shootout_conversion": _ratio(sum(scored for _, scored in kicks), len(kicks)),
    }


def caution_check(matches: Sequence[LeagueMatch]) -> tuple[float, float]:
    """(second yellows per booked player, goals conceded per match by a side after its first
    booking): the caution behaviour's benefit and cost (SC-006)."""
    booked = second = 0
    conceded = sides = 0
    for m in matches:
        report = m.result.report
        if report is None:
            continue
        for side in ("home", "away"):
            yellows = [e for e in report.events if e.side == side and e.kind == "yellow"]
            booked += len(yellows)
            second += sum(1 for e in report.events
                          if e.side == side and e.kind == "second_yellow")
            if yellows:
                first = yellows[0].minute
                sides += 1
                conceded += sum(1 for e in report.events if e.kind in GOAL_KINDS
                                and e.side != side and e.minute > first)
    return _ratio(second, booked), _ratio(conceded, sides)


def late_goal_rates(reports: Iterable[MatchReport]) -> dict[int, float]:
    """Goals per side per minute after minute 75, by the side's goal difference at that minute
    (-1 trailing, 0 level, +1 leading). Real football: late on, a side one goal down scores
    more than a level side, and so does the side one goal up (Lago et al.)."""
    minutes: Counter[int] = Counter()
    goals: Counter[int] = Counter()
    for report in reports:
        timeline = [Minute(m) for m in range(76, 91)] + [
            Minute(90, k) for k in range(1, report.stoppage[1] + 1)]
        goal_events = [e for e in report.events if e.kind in GOAL_KINDS]
        for minute in timeline:
            before = [e for e in goal_events if e.minute < minute]
            now = [e for e in goal_events if e.minute == minute]
            for side in ("home", "away"):
                diff = (sum(e.side == side for e in before)
                        - sum(e.side != side for e in before))
                if -1 <= diff <= 1:
                    minutes[diff] += 1
                    goals[diff] += sum(e.side == side for e in now)
    return {d: goals[d] / minutes[d] for d in (-1, 0, 1)}
