"""Read-only views for clients (spec 005, research R4-R6): the match feed, the news and the
squad table. Everything here derives from the career; nothing is stored."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from manager_core.career import press
from manager_core.career.career import Career
from manager_core.career.discipline import YELLOWS_PER_BAN, Discipline
from manager_core.competition.season import Season
from manager_core.domain.positions import Position
from manager_core.i18n import t
from manager_core.quicksim.report import GOAL_KINDS, MatchReport, Minute
from manager_core.ratings.ability import best_position, current_ability

STOP_EVENT_KINDS = ("draw", "qualified", "relegated", "champion", "title")


# ---- match feed -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FeedLine:
    minute: Minute
    kind: str  # kickoff / half_time / full_time / an event kind
    text: str
    score: tuple[int, int]


def match_feed(season: Season, match_id: str) -> list[FeedLine]:
    """The report's events as a commentary feed with the running score (presentation only)."""
    match = season.matches[match_id]
    report = season.results[match_id].report
    if report is None:
        return []
    names = _names(season, report)
    clubs = {"home": season.club_name(match.home_id), "away": season.club_name(match.away_id)}
    score = [0, 0]
    lines = [FeedLine(Minute(0), "kickoff", t("feed.kickoff", home=clubs["home"],
                                                 away=clubs["away"]), (0, 0))]
    half_time_done = False
    for e in report.events:
        if not half_time_done and e.minute.base > 45:
            lines.append(_half_time(report, clubs, score))
            half_time_done = True
        if e.kind in GOAL_KINDS:
            score[0 if e.side == "home" else 1] += 1
        params = {"club": clubs[e.side], "player": names.get(e.player_id, e.player_id),
                  "other": names.get(e.other_player_id or "", ""),
                  "score": f"{score[0]} x {score[1]}"}
        key = f"feed.{e.kind}" + ("_assist" if e.kind == "goal" and e.other_player_id else "")
        lines.append(FeedLine(e.minute, e.kind, t(key, **params), (score[0], score[1])))
    if not half_time_done:
        lines.append(_half_time(report, clubs, score))
    lines.append(FeedLine(Minute(90, report.stoppage[1]), "full_time",
                          t("feed.full_time", home=clubs["home"], away=clubs["away"],
                            score=f"{score[0]} x {score[1]}"), (score[0], score[1])))
    return lines


def _half_time(report: MatchReport, clubs: dict[str, str], score: list[int]) -> FeedLine:
    return FeedLine(Minute(45, report.stoppage[0]), "half_time",
                    t("feed.half_time", home=clubs["home"], away=clubs["away"],
                      score=f"{score[0]} x {score[1]}"), (score[0], score[1]))


def _names(season: Season, report: MatchReport) -> dict[str, str]:
    ids = {pid for lineup in (report.home_lineup, report.away_lineup)
           for pid in [p for _, p in lineup.starters] + list(lineup.bench)}
    return {pid: season.dataset.player(pid).display_name for pid in ids
            if pid in season.dataset.players}


# ---- news -------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NewsItem:
    day: date
    kind: str  # draw / qualified / relegated / champion / title / result / suspension / season
    text: str


def career_news(career: Career) -> list[NewsItem]:
    season = career.season
    club = career.user_club_id
    items: list[NewsItem] = []
    for e in season.events:
        if e.kind not in STOP_EVENT_KINDS or e.day > career.current_date:
            continue
        names = [season.club_name(c) if c in season.participants else
                 (season.ruleset.stage_name(c) if c in {s.id for s in season.ruleset.stages}
                  else season.ruleset.track_title(c)) for c in e.payload]
        items.append(NewsItem(e.day, e.kind, t(f"event.{e.kind}", detail=", ".join(names))))
    yellows: Counter[str] = Counter()
    for m in season.sorted_matches():
        result = season.results.get(m.id)
        if result is None or club not in (m.home_id, m.away_id):
            continue
        items.append(NewsItem(m.kickoff.date(), "result", t(
            "news.result", home=season.club_name(m.home_id), away=season.club_name(m.away_id),
            score=f"{result.home_goals} x {result.away_goals}")))
        if result.report is None:
            continue
        side = "home" if m.home_id == club else "away"
        sent = {ev.player_id for ev in result.report.events
                if ev.side == side and ev.kind in ("red", "second_yellow")}
        for ev in result.report.events:
            if ev.side != side or ev.kind != "yellow" or ev.player_id in sent:
                continue
            yellows[ev.player_id] += 1
            if yellows[ev.player_id] == YELLOWS_PER_BAN:
                yellows[ev.player_id] = 0
                items.append(NewsItem(m.kickoff.date(), "suspension", t(
                    "news.suspended_yellows", player=season.dataset.player(ev.player_id)
                    .display_name)))
        for pid in sorted(sent):
            items.append(NewsItem(m.kickoff.date(), "suspension", t(
                "news.suspended_red", player=season.dataset.player(pid).display_name)))
    for day, kind, text in press.stories(season, club, career.current_date):
        items.append(NewsItem(day, kind, text))
    for record in career.history:
        world = career.world
        champion = (world.club(record.champion).short_name if record.champion in world.clubs
                    else record.champion)
        items.append(NewsItem(date(record.year, 12, 31), "season", t(
            "news.season", year=record.year, champion=champion, place=record.user_place)))
    return sorted(items, key=lambda n: (n.day, n.kind, n.text), reverse=True)


# ---- squad ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SquadRow:
    player_id: str
    name: str
    position: Position
    age: int
    stars: float  # 0.5-5 relative to the squad (FM style); CA is never shown
    suspended: int  # matches still to serve
    yellows: int  # in the current count toward a ban
    appearances: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int


def squad_view(career: Career) -> list[SquadRow]:
    season, world, club = career.season, career.world, career.user_club_id
    players = sorted(world.squad(club), key=lambda p: (-current_ability(p), p.id))
    n = len(players)
    stars = {p.id: max(0.5, round((5 - 4.5 * i / max(1, n - 1)) * 2) / 2)
             for i, p in enumerate(players)}
    apps: Counter[str] = Counter()
    goals: Counter[str] = Counter()
    assists: Counter[str] = Counter()
    yc: Counter[str] = Counter()
    rc: Counter[str] = Counter()
    for match_id, result in season.results.items():
        m = season.matches[match_id]
        if club not in (m.home_id, m.away_id) or result.report is None:
            continue
        side = "home" if m.home_id == club else "away"
        lineup = result.report.lineup(side)
        apps.update(pid for _, pid in lineup.starters)
        for e in result.report.events:
            if e.side != side:
                continue
            if e.kind == "sub" and e.other_player_id:
                apps[e.other_player_id] += 1
            elif e.kind in ("goal", "penalty_goal"):
                goals[e.player_id] += 1
                if e.other_player_id:
                    assists[e.other_player_id] += 1
            elif e.kind in ("yellow", "second_yellow"):
                yc[e.player_id] += 1
            if e.kind in ("red", "second_yellow"):
                rc[e.player_id] += 1
    ledger = season.discipline if isinstance(season.discipline, Discipline) else None
    return [SquadRow(p.id, p.display_name, best_position(p), p.age(world.reference_date),
                     stars[p.id], ledger.bans(p.id) if ledger else 0,
                     ledger.yellows(p.id) if ledger else 0, apps[p.id], goals[p.id],
                     assists[p.id], yc[p.id], rc[p.id]) for p in players]

