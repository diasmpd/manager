"""The local API's methods (spec 007; contract: contracts/local-api.md). Each one calls the
facade and returns its result; no game rule lives here (Constitution III)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manager_core import __version__, api
from manager_core.career.career import Career
from manager_core.domain.dataset import Dataset
from manager_core.i18n import strings, t
from manager_core.quicksim.params import load_params
from manager_core.server.encode import selection_from_json, tactic_from_json, to_json
from manager_core.server.protocol import Handler, Params, RpcError, Session, param

CONTRACT = "1.2"  # 1.1: tactic.set_role; 1.2: live matches (spec 008)
NEWS_ON_HOME = 5


class Config:
    def __init__(self, saves: Path, data: Path) -> None:
        self.saves = saves
        self.data = data


def _config(s: Session) -> Config:
    config = s.state["config"]
    assert isinstance(config, Config)
    return config


def _career(s: Session) -> Career:
    career = s.state.get("career")
    if career is None:
        raise RpcError("P004", t("server.P004"))
    assert isinstance(career, Career)
    return career


def _dataset(s: Session) -> Dataset:
    if "dataset" not in s.state:
        loaded = api.load_dataset(_config(s).data)
        if loaded.dataset is None:
            raise RpcError("P005", t("server.P005", detail=str(_config(s).data)))
        s.state["dataset"] = loaded.dataset
    dataset = s.state["dataset"]
    assert isinstance(dataset, Dataset)
    return dataset


def _open(s: Session, career: Career) -> None:
    previous = s.state.get("career")
    if previous is not None:
        api.save_career(previous, _config(s).saves)
    s.state["career"] = career


def map_errors(exc: Exception) -> RpcError | None:
    """Facade errors as contract errors, with the core's PT-BR message."""
    if isinstance(exc, api.NotFoundError):
        return RpcError("NOT_FOUND", t("server.not_found", kind=exc.kind, id=exc.id),
                        {"kind": exc.kind, "id": exc.id})
    if isinstance(exc, api.SelectionError):
        return RpcError("SELECTION", t("server.selection",
                                       problems=", ".join(i.code for i in exc.issues)),
                        {"issues": exc.issues})
    if isinstance(exc, api.LiveMatchError):
        return RpcError("MATCH", exc.message, {"match_code": exc.code})
    if isinstance(exc, api.TacticError):
        return RpcError("TACTIC", t("server.tactic",
                                    problems=", ".join(f"{i.code} {i.path}" for i in exc.issues)),
                        {"issues": exc.issues})
    return None


# ---- session ---------------------------------------------------------------------------------


def hello(s: Session, p: Params) -> Any:
    param(p, "client", str)
    return {"contract": CONTRACT, "core_version": __version__,
            "model_version": load_params().model_version, "strings": strings("")}


def shutdown(s: Session, p: Params) -> Any:
    career = s.state.get("career")
    if career is not None:
        api.save_career(career, _config(s).saves)
    s.stop = True
    return {"saved": career is not None}


# ---- careers ---------------------------------------------------------------------------------


def career_list(s: Session, p: Params) -> Any:
    return api.list_saves(_config(s).saves)


def career_clubs(s: Session, p: Params) -> Any:
    return [{"id": c.id, "name": c.name, "reputation": c.reputation}
            for c in api.list_clubs(_dataset(s))]


def career_new(s: Session, p: Params) -> Any:
    name = param(p, "name", str)
    club_id = param(p, "club_id", str)
    if any(summary.name == name for summary in api.list_saves(_config(s).saves)):
        raise RpcError("SAVE", t("server.duplicate_career", name=name), {"save_code": "duplicate"})
    career = api.new_career(_dataset(s), name, club_id)
    api.save_career(career, _config(s).saves)
    _open(s, career)
    return api.career_status(career)


def career_open(s: Session, p: Params) -> Any:
    career = api.load_career(_config(s).saves, param(p, "name", str))
    _open(s, career)
    notices = list(career.notices)
    career.notices.clear()
    return {"status": api.career_status(career), "notices": notices}


def career_save(s: Session, p: Params) -> Any:
    return {"path": str(api.save_career(_career(s), _config(s).saves))}


def career_status(s: Session, p: Params) -> Any:
    return api.career_status(_career(s))


def career_continue(s: Session, p: Params) -> Any:
    career = _career(s)
    s.state.pop("live", None)
    s.state.pop("live_sent", None)
    if not param(p, "to_season_end", bool, False):
        return api.continue_career(career, _config(s).saves)
    while True:  # stop by stop, so the client sees progress (research R3)
        stop = api.continue_career(career, _config(s).saves)
        s.notify("progress", {"day": career.current_date,
                              "played": len(career.season.results)})
        if stop.kind == "season_end":
            return stop


# ---- team selection --------------------------------------------------------------------------


def selection_current(s: Session, p: Params) -> Any:
    career = _career(s)
    current = career.selection
    valid = current is not None and not any(
        i.severity == "error" for i in api.validate_selection(career, current))
    selection = current if valid else api.propose_selection(career)
    return {"selection": selection, "positions": api.formation_positions(selection.formation),
            "squad": api.squad_view(career)}


def selection_propose(s: Session, p: Params) -> Any:
    return api.propose_selection(_career(s), param(p, "formation", str, None))


def selection_swap(s: Session, p: Params) -> Any:
    return api.swap_in_selection(_career(s), selection_from_json(param(p, "selection", dict)),
                                 param(p, "slot", int), param(p, "player_id", str))


def selection_validate(s: Session, p: Params) -> Any:
    return api.validate_selection(_career(s), selection_from_json(param(p, "selection", dict)))


def selection_confirm(s: Session, p: Params) -> Any:
    career = _career(s)
    selection = selection_from_json(param(p, "selection", dict))
    changes = api.tactic_changes(career, selection.formation)
    issues = api.confirm_selection(career, selection)
    return {"issues": issues, "tactic_changes": changes}


def formations_list(s: Session, p: Params) -> Any:
    return [{"name": f.name, "positions": api.formation_positions(f.name)}
            for f in api.list_formations()]


# ---- tactics ---------------------------------------------------------------------------------


def tactic_options(s: Session, p: Params) -> Any:
    return api.tactic_options()


def tactic_current(s: Session, p: Params) -> Any:
    return api.current_tactic(_career(s))


def tactic_default(s: Session, p: Params) -> Any:
    return api.default_tactic(param(p, "formation", str))


def tactic_suggest_oop(s: Session, p: Params) -> Any:
    return api.suggest_oop_formations(param(p, "formation", str))


def tactic_roles(s: Session, p: Params) -> Any:
    position = param(p, "position", str)
    phase = param(p, "phase", str)
    if phase not in ("ip", "oop"):
        raise RpcError("P003", t("server.P003", detail="phase"))
    try:
        return api.valid_roles(position, phase)
    except ValueError:
        raise api.NotFoundError("position", position) from None


def tactic_suitability(s: Session, p: Params) -> Any:
    career = _career(s)
    pairs = param(p, "pairs", list)
    if not all(isinstance(x, list) and len(x) == 2 and all(isinstance(v, str) for v in x)
               for x in pairs):
        raise RpcError("P003", t("server.P003", detail="pairs"))
    return [api.role_suitability(career, pid, role) for pid, role in pairs]


def tactic_set_role(s: Session, p: Params) -> Any:
    phase = param(p, "phase", str)
    if phase not in ("ip", "oop"):
        raise RpcError("P003", t("server.P003", detail="phase"))
    return api.set_role(tactic_from_json(param(p, "tactic", dict)), param(p, "slot", int), phase,
                        param(p, "role_id", str))


def tactic_validate(s: Session, p: Params) -> Any:
    return api.validate_tactic(_career(s), tactic_from_json(param(p, "tactic", dict)))


def tactic_confirm(s: Session, p: Params) -> Any:
    api.confirm_tactic(_career(s), tactic_from_json(param(p, "tactic", dict)))
    return {}


# ---- live matches (spec 008) ------------------------------------------------------------------


def _live(s: Session) -> api.LiveSession:
    session = s.state.get("live")
    if session is None:
        raise RpcError("MATCH", t("live.no_session"), {"match_code": "no_session"})
    assert isinstance(session, api.LiveSession)
    return session


def _live_view(s: Session) -> Any:
    career, session = _career(s), _live(s)
    feed = api.live_feed(career, session)
    sent = int(s.state.get("live_sent", 0))
    s.state["live_sent"] = len(feed)
    return {"feed": feed[sent:], "state": api.live_state(career, session),
            "finished": session.match.finished}


def match_start(s: Session, p: Params) -> Any:
    career = _career(s)
    session = api.start_live_match(career)
    s.state["live"] = session
    s.state["live_sent"] = 0
    return {"match": api.match_view(career.season, session.match_id), "side": session.user_side,
            **_live_view(s)}


def match_advance(s: Session, p: Params) -> Any:
    seconds = param(p, "seconds", (int, float))
    api.live_advance(_live(s), float(seconds))
    return _live_view(s)


def match_state(s: Session, p: Params) -> Any:
    return api.live_state(_career(s), _live(s))


def match_substitute(s: Session, p: Params) -> Any:
    api.live_substitute(_live(s), param(p, "off", str), param(p, "on", str))
    return api.live_state(_career(s), _live(s))


def match_tactic(s: Session, p: Params) -> Any:
    api.live_tactic(_career(s), _live(s), tactic_from_json(param(p, "tactic", dict)))
    return api.live_state(_career(s), _live(s))


def match_finish(s: Session, p: Params) -> Any:
    career, session = _career(s), _live(s)
    stop = api.finish_live_match(career, session, _config(s).saves)
    s.state.pop("live", None)
    s.state.pop("live_sent", None)
    return {"stop": stop, "match_id": session.match_id}


# ---- views -----------------------------------------------------------------------------------


def view_home(s: Session, p: Params) -> Any:
    return api.home_view(_career(s), NEWS_ON_HOME)


def view_squad(s: Session, p: Params) -> Any:
    return api.squad_view(_career(s))


def view_player(s: Session, p: Params) -> Any:
    return api.player_profile(_career(s).world, param(p, "player_id", str))


def view_table(s: Session, p: Params) -> Any:
    season = _career(s).season
    rows = api.season_table(season, param(p, "group", str, None))
    return [{**to_json(r), "club_name": season.club_name(r.club_id)} for r in rows]


def view_groups(s: Session, p: Params) -> Any:
    return api.season_groups(_career(s).season)


def view_fixtures(s: Session, p: Params) -> Any:
    return api.season_fixtures(_career(s).season, param(p, "club_id", str, None))


def view_calendar(s: Session, p: Params) -> Any:
    career = _career(s)
    season = career.season
    club = career.user_club_id
    days = []
    for day in api.season_calendar(season, param(p, "month", int)):
        mine = [mid for mid in day.match_ids
                if club in (season.matches[mid].home_id, season.matches[mid].away_id)]
        days.append({"day": day.day,
                     "user_match": api.match_view(season, mine[0]) if mine else None,
                     "match_count": len(day.match_ids),
                     "windows": list(dict.fromkeys(w.name for w in day.windows)),
                     "events": day.events})
    return days


def view_news(s: Session, p: Params) -> Any:
    return api.career_news(_career(s))


def view_match(s: Session, p: Params) -> Any:
    season = _career(s).season
    match_id = param(p, "match_id", str)
    match = api.match_view(season, match_id)
    played = match.result is not None and match.result.report is not None
    return {"match": match, "feed": api.match_feed(season, match_id) if played else [],
            "stats": api.match_stats(season, match_id)}


def view_last_user_match(s: Session, p: Params) -> Any:
    return {"match_id": api.last_user_match(_career(s))}


METHODS: dict[str, Handler] = {
    "hello": hello, "shutdown": shutdown,
    "career.list": career_list, "career.clubs": career_clubs, "career.new": career_new,
    "career.open": career_open, "career.save": career_save, "career.status": career_status,
    "career.continue": career_continue,
    "selection.current": selection_current, "selection.propose": selection_propose,
    "selection.swap": selection_swap, "selection.validate": selection_validate,
    "selection.confirm": selection_confirm, "formations.list": formations_list,
    "tactic.options": tactic_options, "tactic.current": tactic_current,
    "tactic.default": tactic_default, "tactic.suggest_oop": tactic_suggest_oop,
    "tactic.roles": tactic_roles, "tactic.suitability": tactic_suitability,
    "tactic.set_role": tactic_set_role,
    "tactic.validate": tactic_validate, "tactic.confirm": tactic_confirm,
    "match.start": match_start, "match.advance": match_advance, "match.state": match_state,
    "match.substitute": match_substitute, "match.tactic": match_tactic,
    "match.finish": match_finish,
    "view.home": view_home, "view.squad": view_squad, "view.player": view_player,
    "view.table": view_table, "view.groups": view_groups, "view.fixtures": view_fixtures,
    "view.calendar": view_calendar, "view.news": view_news, "view.match": view_match,
    "view.last_user_match": view_last_user_match,
}
