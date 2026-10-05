"""Explicit JSON codecs for results and match reports (spec 004, research R3).

Every field is written and read by name, so a missing field fails loudly (KeyError) and a
decoded object equals the original. Pickle is never used: it would tie saves to class layouts.
"""

from __future__ import annotations

from typing import Any

from manager_core.competition.results import Result, Shootout
from manager_core.domain.positions import Position
from manager_core.quicksim.report import (
    MatchEvent,
    MatchReport,
    Minute,
    SideLineup,
    SideStats,
    TacticSummary,
)

Json = dict[str, Any]


def encode_result(r: Result) -> Json:
    return {
        "home_goals": r.home_goals, "away_goals": r.away_goals, "source": r.source,
        "home_red": r.home_red, "away_red": r.away_red,
        "home_yellow": r.home_yellow, "away_yellow": r.away_yellow,
        "shootout": None if r.shootout is None else {
            "kicks": [[club, scored] for club, scored in r.shootout.kicks],
            "winner_id": r.shootout.winner_id,
        },
        "report": None if r.report is None else encode_report(r.report),
    }


def decode_result(d: Json) -> Result:
    shootout = d["shootout"]
    report = d["report"]
    return Result(
        d["home_goals"], d["away_goals"], d["source"],
        home_red=d["home_red"], away_red=d["away_red"],
        home_yellow=d["home_yellow"], away_yellow=d["away_yellow"],
        shootout=None if shootout is None else Shootout(
            tuple((club, bool(scored)) for club, scored in shootout["kicks"]),
            shootout["winner_id"]),
        report=None if report is None else decode_report(report),
    )


def _stats(s: SideStats) -> Json:
    return {"goals": s.goals, "shots": s.shots, "shots_on_target": s.shots_on_target,
            "xg": s.xg, "possession": s.possession, "corners": s.corners, "fouls": s.fouls,
            "yellows": s.yellows, "reds": s.reds}


def _stats_back(d: Json) -> SideStats:
    return SideStats(d["goals"], d["shots"], d["shots_on_target"], d["xg"], d["possession"],
                     d["corners"], d["fouls"], d["yellows"], d["reds"])


def _event(e: MatchEvent) -> Json:
    return {"minute": [e.minute.base, e.minute.added], "side": e.side, "kind": e.kind,
            "player_id": e.player_id, "other_player_id": e.other_player_id, "xg": e.xg}


def _event_back(d: Json) -> MatchEvent:
    base, added = d["minute"]
    return MatchEvent(Minute(base, added), d["side"], d["kind"], d["player_id"],
                      d["other_player_id"], d["xg"])


def _lineup(lineup: SideLineup) -> Json:
    return {"club_id": lineup.club_id, "formation": lineup.formation,
            "starters": [[pos.value, pid] for pos, pid in lineup.starters],
            "bench": list(lineup.bench), "flags": list(lineup.flags)}


def _lineup_back(d: Json) -> SideLineup:
    return SideLineup(d["club_id"], d["formation"],
                      tuple((Position(pos), pid) for pos, pid in d["starters"]),
                      tuple(d["bench"]), tuple(d["flags"]))


def _tactic(t: TacticSummary | None) -> Json | None:
    if t is None:
        return None
    return {"ip_formation": t.ip_formation, "oop_formation": t.oop_formation,
            "mentality": t.mentality, "style": t.style, "digest": t.digest}


def _tactic_back(d: Json | None) -> TacticSummary | None:
    if d is None:
        return None
    return TacticSummary(d["ip_formation"], d["oop_formation"], d["mentality"], d["style"],
                         d["digest"])


def encode_report(r: MatchReport) -> Json:
    return {
        "home": _stats(r.home), "away": _stats(r.away),
        "events": [_event(e) for e in r.events],
        "home_lineup": _lineup(r.home_lineup), "away_lineup": _lineup(r.away_lineup),
        "home_finishers": list(r.home_finishers), "away_finishers": list(r.away_finishers),
        "stoppage": list(r.stoppage), "model_version": r.model_version,
        "home_keeper": r.home_keeper, "away_keeper": r.away_keeper,
        "home_tactic": _tactic(r.home_tactic), "away_tactic": _tactic(r.away_tactic),
    }


def decode_report(d: Json) -> MatchReport:
    first, second = d["stoppage"]
    return MatchReport(
        home=_stats_back(d["home"]), away=_stats_back(d["away"]),
        events=tuple(_event_back(e) for e in d["events"]),
        home_lineup=_lineup_back(d["home_lineup"]), away_lineup=_lineup_back(d["away_lineup"]),
        home_finishers=tuple(d["home_finishers"]), away_finishers=tuple(d["away_finishers"]),
        stoppage=(first, second), model_version=d["model_version"],
        home_keeper=d["home_keeper"], away_keeper=d["away_keeper"],
        home_tactic=_tactic_back(d.get("home_tactic")),  # absent in reports saved before 006
        away_tactic=_tactic_back(d.get("away_tactic")),
    )
