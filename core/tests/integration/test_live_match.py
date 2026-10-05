"""Live matches through the local API (spec 008 T015, contract 1.2): the client drives the clock,
pauses by not advancing, substitutes and changes the tactic within the rules; a live match with
no decisions equals the same match played in the background."""

import json
from pathlib import Path
from typing import Any

import pytest

from manager_core import api
from manager_core.server.methods import METHODS, Config, map_errors
from manager_core.server.protocol import Session, handle_line

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


class Client:
    def __init__(self, saves: Path) -> None:
        import io

        self.out = io.StringIO()
        self.session = Session(self.out)
        self.session.state["config"] = Config(saves, SAMPLE)
        self.next_id = 0

    def raw(self, method: str, **params: Any) -> dict[str, Any]:
        self.next_id += 1
        start = len(self.out.getvalue())
        handle_line(self.session, METHODS, json.dumps(
            {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}),
            map_errors)
        return [json.loads(m) for m in self.out.getvalue()[start:].splitlines()][-1]

    def call(self, method: str, **params: Any) -> Any:
        answer = self.raw(method, **params)
        assert "result" in answer, answer
        return answer["result"]

    def error(self, method: str, **params: Any) -> dict[str, Any]:
        answer = self.raw(method, **params)
        assert "error" in answer, answer
        return answer["error"]


def _to_user_match(client: Client) -> None:
    for _ in range(40):
        stop = client.call("career.continue")
        if stop["kind"] == "user_match":
            return
    raise AssertionError("no user match reached")


@pytest.fixture
def live(tmp_path: Path) -> Client:
    client = Client(tmp_path)
    client.call("career.new", name="ao-vivo", club_id="mineracao")
    _to_user_match(client)
    return client


def test_no_match_no_session(tmp_path: Path) -> None:
    client = Client(tmp_path)
    client.call("career.new", name="sem-jogo", club_id="mineracao")
    assert client.error("match.start")["data"]["match_code"] == "no_match"
    assert client.error("match.advance", seconds=10)["data"]["match_code"] == "no_session"


def test_the_clock_is_driven_by_the_client(live: Client) -> None:
    started = live.call("match.start")
    assert started["side"] in ("home", "away")
    assert started["state"]["minute"]["base"] == 1 and not started["finished"]
    kinds = [line["kind"] for line in started["feed"]]
    assert kinds == ["kickoff"]
    seen = list(started["feed"])
    paused = live.call("match.advance", seconds=20 * 60)
    assert 19 <= paused["state"]["minute"]["base"] <= 21
    seen += paused["feed"]
    # pausing is not advancing: the state stays put
    assert live.call("match.state")["minute"] == paused["state"]["minute"]
    while True:
        step = live.call("match.advance", seconds=600)
        seen += step["feed"]
        if step["finished"]:
            break
    kinds = [line["kind"] for line in seen]
    assert kinds.count("kickoff") == 1 and kinds.count("half_time") == 1
    assert kinds[-1] == "full_time"


def test_substitutions_follow_the_rules(live: Client) -> None:
    state = live.call("match.start")["state"]
    # a decision at kick-off: from now on the manager makes his own substitutions (the
    # assistant's random ones would change the counts below)
    live.call("match.tactic", tactic=state["tactic"])
    live.call("match.advance", seconds=55 * 60)
    on_pitch = [p for p in state["on_pitch"] if p["position"] != "GK"]
    bench = [p["player_id"] for p in state["bench"]]
    after = live.call("match.substitute", off=on_pitch[0]["player_id"], on=bench[0])
    ids = {p["player_id"] for p in after["on_pitch"]}
    assert bench[0] in ids and on_pitch[0]["player_id"] not in ids
    assert after["subs_left"] == 4 and after["windows_left"] == 2
    # the same pause uses the same window
    second = live.call("match.substitute", off=on_pitch[1]["player_id"], on=bench[1])
    assert second["windows_left"] == 2
    assert live.error("match.substitute", off=on_pitch[0]["player_id"],
                      on=bench[2])["data"]["match_code"] == "not_on_pitch"
    assert live.error("match.substitute", off=on_pitch[2]["player_id"],
                      on=bench[0])["data"]["match_code"] == "not_on_bench"
    live.call("match.advance", seconds=60)
    live.call("match.substitute", off=on_pitch[2]["player_id"], on=bench[2])
    live.call("match.advance", seconds=60)
    third = live.call("match.substitute", off=on_pitch[3]["player_id"], on=bench[3])
    assert third["windows_left"] == 0 and third["subs_left"] == 1
    live.call("match.advance", seconds=60)
    assert live.error("match.substitute", off=on_pitch[4]["player_id"],
                      on=bench[4])["data"]["match_code"] == "sub_window"


def test_a_tactic_change_acts_from_now(live: Client) -> None:
    state = live.call("match.start")["state"]
    tactic = dict(state["tactic"])
    other = "4-3-3" if tactic["ip_formation"] != "4-3-3" else "4-4-2"
    wrong = dict(live.call("tactic.default", formation=other))
    assert live.error("match.tactic", tactic=wrong)["data"]["match_code"] == "formation_change"
    tactic["mentality"] = "very_attacking"
    changed = live.call("match.tactic", tactic=tactic)
    assert changed["tactic"]["mentality"] == "very_attacking"


def test_finishing_commits_and_continues(live: Client) -> None:
    match_id = live.call("match.start")["match"]["id"]
    done = live.call("match.finish")
    assert done["match_id"] == match_id
    assert done["stop"]["kind"] in ("user_match", "event", "season_end")
    played = live.call("view.match", match_id=match_id)
    assert played["match"]["result"] is not None and played["feed"]
    assert played["match"]["result"]["source"] == "positional"
    assert live.error("match.advance", seconds=1)["data"]["match_code"] == "no_session"


def test_a_live_match_without_decisions_equals_the_background_one(tmp_path: Path) -> None:
    live = Client(tmp_path / "live")
    live.call("career.new", name="igual", club_id="mineracao")
    _to_user_match(live)
    match_id = live.call("match.start")["match"]["id"]
    live.call("match.finish")
    served = live.session.state["career"]
    world = api.load_dataset(SAMPLE).dataset
    assert world is not None
    direct = api.new_career(world, "igual", "mineracao", master_seed=served.master_seed)
    while True:
        stop = api.continue_career(direct, tmp_path / "direct")
        if stop.kind == "user_match":
            api.continue_career(direct, tmp_path / "direct")  # plays it in the background
            break
    assert served.season.results[match_id] == direct.season.results[match_id]


def test_records_are_saved_and_survive_load(tmp_path: Path) -> None:
    """Spec 008 FR-004 / T016: the user's match records are saved (format v4) and read back."""
    import sqlite3

    from manager_core.career.store import FORMAT_VERSION, path_for

    client = Client(tmp_path)
    client.call("career.new", name="registro", club_id="mineracao")
    _to_user_match(client)
    match_id = client.call("match.start")["match"]["id"]
    client.call("match.finish")
    client.call("career.save")
    career = api.load_career(tmp_path, "registro")
    record = api.match_record(career, match_id)
    assert record is not None and len(record.players) == 22
    assert len(record.samples) > 90 * 60  # 2 Hz over the whole match
    assert FORMAT_VERSION == 4
    # a format-3 save (spec 006) has no records table: it migrates and loads without records
    with sqlite3.connect(path_for(tmp_path, "registro")) as conn:
        conn.execute("DROP TABLE records")
        conn.execute("PRAGMA user_version = 3")
    conn.close()
    old = api.load_career(tmp_path, "registro")
    assert api.match_record(old, match_id) is None
