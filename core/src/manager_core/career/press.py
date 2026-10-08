"""Original match, player and team news, written by the game from its own data (no outlet's text).

Match reports come from the match report of the quick sim or the positional engine (goals, minutes,
xG, shots, possession). Player and team items come from the same facts over the season so far.
Wording lives in the PT-BR catalogue; the variant is chosen from the match id, so the same match
always gets the same words.
"""

from __future__ import annotations

import random
from datetime import date

from manager_core.competition.season import Season
from manager_core.i18n import t
from manager_core.quicksim.report import MatchReport

VARIANTS = 3
STREAK_WINS = 3
STREAK_UNBEATEN = 5
HAT_TRICK = 3


def _pick(key: str, seed: str, variants: int = VARIANTS) -> str:
    return f"{key}.{random.Random(f'press:{seed}').randrange(variants)}"


def _headline(goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        margin = goals_for - goals_against
        return "win_big" if margin >= 3 else "win_close" if margin == 1 else "win"
    if goals_for == goals_against:
        return "draw"
    return "loss_big" if goals_against - goals_for >= 3 else "loss"


def _minute(event_minute: object) -> int:
    base = getattr(event_minute, "base", 0)
    added = getattr(event_minute, "added", 0)
    return int(base) + int(added)


def _scorers(season: Season, report: MatchReport, side: str) -> list[tuple[str, int]]:
    """(player name, minute) for each goal the side scored, in order."""
    goal_kinds = {"goal", "penalty_goal"}
    out: list[tuple[str, int]] = []
    for ev in report.events:
        if ev.kind in goal_kinds and ev.side == side:
            name = season.dataset.player(ev.player_id).display_name
            out.append((name, _minute(ev.minute)))
        elif ev.kind == "own_goal" and ev.side == side:
            name = season.dataset.player(ev.player_id).display_name
            out.append((name + " (contra)", _minute(ev.minute)))
    return out


def _xg_comment(goals: int, xg: float, seed: str) -> str:
    if goals - xg >= 1.0:
        return t(_pick("press.xg.above", seed), xg=f"{xg:.1f}".replace(".", ","))
    if xg - goals >= 1.0:
        return t(_pick("press.xg.below", seed), xg=f"{xg:.1f}".replace(".", ","))
    return t(_pick("press.xg.level", seed), xg=f"{xg:.1f}".replace(".", ","))


def match_report(season: Season, match_id: str, home_id: str, away_id: str,
                 home_goals: int, away_goals: int, report: MatchReport, club: str) -> list[str]:
    """Headline and story lines for one match, from the club's point of view."""
    side = "home" if club == home_id else "away"
    mine, theirs = (home_goals, away_goals) if side == "home" else (away_goals, home_goals)
    mine_stats = report.home if side == "home" else report.away
    their_name = season.club_name(away_id if side == "home" else home_id)
    kind = _headline(mine, theirs)
    lines = [t(_pick("press.headline." + kind, match_id), opponent=their_name,
               score=f"{mine} x {theirs}")]
    scorers = _scorers(season, report, side)
    if scorers:
        lines.append(t("press.scorers", scorers="; ".join(f"{n} ({m}')" for n, m in scorers)))
    lines.append(_xg_comment(mine, mine_stats.xg, match_id + side))
    lines.append(t(_pick("press.shots", match_id + side), shots=mine_stats.shots,
                   on_target=mine_stats.shots_on_target, possession=mine_stats.possession))
    return lines


def _player_items(season: Season, match_id: str, report: MatchReport, side: str,
                  day: date, out: list[tuple[date, str, str]]) -> None:
    goals: dict[str, int] = {}
    for ev in report.events:
        if ev.kind in ("goal", "penalty_goal") and ev.side == side:
            goals[ev.player_id] = goals.get(ev.player_id, 0) + 1
    for pid, count in goals.items():
        if count >= HAT_TRICK:
            name = season.dataset.player(pid).display_name
            out.append((day, "press.player.hat_trick", t("press.player.hat_trick", player=name,
                                                         goals=count)))


def season_news(season: Season, club: str, until: date) -> list[tuple[date, str, str]]:
    """Team and player items for the club, for matches played up to `until`:
    player hat-tricks, and winning / unbeaten runs, with the day they were reached."""
    items: list[tuple[date, str, str]] = []
    played = []
    for m in season.sorted_matches():
        result = season.results.get(m.id)
        if result is None or club not in (m.home_id, m.away_id) or m.kickoff.date() > until:
            continue
        played.append((m, result))
    wins = unbeaten = 0
    for m, result in played:
        side = "home" if club == m.home_id else "away"
        mine, theirs = ((result.home_goals, result.away_goals) if side == "home"
                        else (result.away_goals, result.home_goals))
        day = m.kickoff.date()
        if result.report is not None:
            _player_items(season, m.id, result.report, side, day, items)
        wins = wins + 1 if mine > theirs else 0
        unbeaten = unbeaten + 1 if mine >= theirs else 0
        if wins == STREAK_WINS:
            items.append((day, "press.team.streak", t("press.team.streak", n=wins)))
        if unbeaten == STREAK_UNBEATEN:
            items.append((day, "press.team.unbeaten", t("press.team.unbeaten", n=unbeaten)))
    return items


def stories(season: Season, club: str, until: date) -> list[tuple[date, str, str]]:
    """Everything the press writes about the club up to `until`: a headline with its story for
    each match that has a report, plus player and team items. (day, kind, text), newest first
    when sorted by the caller."""
    out: list[tuple[date, str, str]] = []
    for m in season.sorted_matches():
        result = season.results.get(m.id)
        if result is None or result.report is None or club not in (m.home_id, m.away_id):
            continue
        if m.kickoff.date() > until:
            continue
        lines = match_report(season, m.id, m.home_id, m.away_id, result.home_goals,
                             result.away_goals, result.report, club)
        sentences = [line if line.endswith((".", "!")) else line + "." for line in lines]
        out.append((m.kickoff.date(), "match", " ".join(sentences)))
    out.extend(season_news(season, club, until))
    return out
