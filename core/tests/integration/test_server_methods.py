"""Every local API method (spec 007 T005-T011, SC-003), the parity season (SC-002) and the real
process (FR-006)."""

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from manager_core import api
from manager_core.server.methods import CONTRACT as CONTRACT_VERSION
from manager_core.server.methods import METHODS, Config, map_errors
from manager_core.server.protocol import Session, handle_line

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


class Client:
    """Talks to the server in-process, through the real protocol code."""

    def __init__(self, saves: Path) -> None:
        self.out = io.StringIO()
        self.session = Session(self.out)
        self.session.state["config"] = Config(saves, SAMPLE)
        self.next_id = 0
        self.notifications: list[dict[str, Any]] = []

    def raw(self, method: str, **params: Any) -> dict[str, Any]:
        self.next_id += 1
        start = len(self.out.getvalue())
        line = json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method,
                           "params": params})
        handle_line(self.session, METHODS, line, map_errors)
        messages = [json.loads(m) for m in self.out.getvalue()[start:].splitlines()]
        self.notifications += [m for m in messages if "id" not in m]
        answer = messages[-1]
        assert answer["id"] == self.next_id
        return answer

    def call(self, method: str, **params: Any) -> Any:
        answer = self.raw(method, **params)
        assert "result" in answer, answer
        return answer["result"]

    def error(self, method: str, **params: Any) -> dict[str, Any]:
        answer = self.raw(method, **params)
        assert "error" in answer, answer
        return answer["error"]


@pytest.fixture
def client(tmp_path: Path) -> Client:
    return Client(tmp_path)


@pytest.fixture
def playing(client: Client) -> Client:
    client.call("career.new", name="jogo", club_id="alvorada")
    return client


def test_every_contract_method_is_served() -> None:
    contract = (Path(__file__).resolve().parents[3] / "contracts" / "local-api.md").read_text(
        "utf-8")
    documented = {m for m in METHODS if f"`{m}`" in contract}
    assert documented == set(METHODS)


def test_hello(client: Client) -> None:
    hello = client.call("hello", client="test")
    assert hello["contract"] == CONTRACT_VERSION
    assert hello["core_version"] and hello["model_version"]
    assert hello["strings"]["ui.continue"] == "Continuar"
    assert hello["strings"]["month.2"] and hello["strings"]["table.pts"]


def test_no_career_yet(client: Client) -> None:
    assert client.call("career.list") == []
    for method in ("career.status", "career.continue", "view.home", "selection.current",
                   "tactic.current", "view.squad"):
        assert client.error(method)["code"] == "P004"


def test_careers(client: Client, tmp_path: Path) -> None:
    clubs = client.call("career.clubs")
    assert len(clubs) == 12 and {"id", "name", "reputation"} <= set(clubs[0])
    status = client.call("career.new", name="minha", club_id="alvorada")
    assert status["club_id"] == "alvorada" and status["name"] == "minha"
    assert client.error("career.new", name="minha", club_id="alvorada")["code"] == "SAVE"
    assert client.error("career.new", name="Bad Name!", club_id="alvorada")["code"] == "SAVE"
    assert client.error("career.new", name="outra", club_id="nope")["code"] == "NOT_FOUND"
    assert [s["name"] for s in client.call("career.list")] == ["minha"]
    opened = client.call("career.open", name="minha")
    assert opened["status"]["name"] == "minha" and opened["notices"] == []
    assert client.error("career.open", name="ghost")["code"] == "NOT_FOUND"
    assert client.call("career.save")["path"].endswith("minha.sqlite")
    status = client.call("career.status")
    assert status["current_date"]
    # contract 1.3: the user club's colours, from the dataset (alvorada: red and white)
    assert status["club_colors"] == ["#C8102E", "#FFFFFF"]


def test_continue_and_progress(playing: Client) -> None:
    stop = playing.call("career.continue")
    assert stop["kind"] in ("user_match", "event", "season_end")
    home = playing.call("view.home")
    assert {"status", "last_match", "news"} <= set(home)
    end = playing.call("career.continue", to_season_end=True)
    assert end["kind"] == "season_end"
    progress = [n for n in playing.notifications if n["method"] == "progress"]
    assert progress and progress[-1]["params"]["played"] > 0
    assert all(n["params"]["request"] == playing.next_id for n in progress)
    match_id = playing.call("view.last_user_match")["match_id"]
    match = playing.call("view.match", match_id=match_id)
    assert match["feed"] and match["feed"][0]["kind"] == "kickoff"
    assert [row[0] for row in match["stats"]][:2] == ["Finalizações", "No alvo"]


def test_selection(playing: Client) -> None:
    current = playing.call("selection.current")
    selection = current["selection"]
    assert len(selection["starters"]) == 11 and len(current["positions"]) == 11
    assert len(current["squad"]) >= 18
    proposed = playing.call("selection.propose", formation="4-3-3")
    assert proposed["formation"] == "4-3-3"
    bench_player = selection["bench"][0]
    swapped = playing.call("selection.swap", selection=selection, slot=10,
                           player_id=bench_player)
    assert [10, bench_player] in swapped["starters"]
    assert playing.call("selection.validate", selection=swapped) == []
    confirmed = playing.call("selection.confirm", selection=swapped)
    assert confirmed == {"issues": [], "tactic_changes": []}
    bad = dict(swapped, starters=[[i, "ghost"] for i, _ in swapped["starters"]])
    error = playing.error("selection.confirm", selection=bad)
    assert error["code"] == "SELECTION" and error["data"]["issues"]
    assert playing.error("selection.swap", selection={"x": 1}, slot=1,
                         player_id="p")["code"] == "P003"
    formations = playing.call("formations.list")
    assert any(f["name"] == "4-4-2" and len(f["positions"]) == 11 for f in formations)


def test_tactics(playing: Client) -> None:
    options = playing.call("tactic.options")
    assert len(options["mentality"]["settings"]) == 7
    tactic = playing.call("tactic.current")
    assert playing.call("tactic.validate", tactic=tactic) == []
    assert playing.call("tactic.default", formation="4-3-3")["ip_formation"] == "4-3-3"
    assert playing.call("tactic.suggest_oop", formation="4-3-3")
    roles = playing.call("tactic.roles", position="DC", phase="ip")
    assert roles and all("DC" in r["positions"] for r in roles)
    assert playing.error("tactic.roles", position="DC", phase="x")["code"] == "P003"
    assert playing.error("tactic.roles", position="ZZ", phase="ip")["code"] == "NOT_FOUND"
    squad = playing.call("view.squad")
    values = playing.call("tactic.suitability",
                          pairs=[[squad[0]["player_id"], roles[0]["id"]]])
    assert len(values) == 1 and 1 <= values[0] <= 20
    oop_roles = playing.call("tactic.roles", position=squad_position(playing, tactic, 1),
                             phase="oop")
    wanted = oop_roles[-1]["id"]
    set_role = playing.call("tactic.set_role", tactic=tactic, slot=1, phase="oop",
                            role_id=wanted)
    assert set_role["slots"][1]["oop_role"] == wanted
    assert playing.call("tactic.validate", tactic=set_role) == []
    assert playing.error("tactic.set_role", tactic=tactic, slot=1, phase="oop",
                         role_id="no_such_role")["code"] == "NOT_FOUND"
    assert playing.error("tactic.set_role", tactic=tactic, slot=99, phase="ip",
                         role_id=roles[0]["id"])["code"] == "NOT_FOUND"
    changed = dict(tactic, mentality="positive")
    assert playing.call("tactic.confirm", tactic=changed) == {}
    assert playing.call("tactic.current")["mentality"] == "positive"
    error = playing.error("tactic.confirm", tactic=dict(tactic, mentality="kamikaze"))
    assert error["code"] == "TACTIC" and error["data"]["issues"][0]["code"] == "T001"


def squad_position(client: Client, tactic: dict[str, Any], slot: int) -> str:
    formations = client.call("formations.list")
    positions = next(f["positions"] for f in formations if f["name"] == tactic["ip_formation"])
    return str(positions[slot])


def test_views(playing: Client) -> None:
    squad = playing.call("view.squad")
    player = playing.call("view.player", player_id=squad[0]["player_id"])
    assert player["player_id"] == squad[0]["player_id"] and player["attributes"]
    assert playing.error("view.player", player_id="ghost")["code"] == "NOT_FOUND"
    groups = playing.call("view.groups")
    assert groups
    assert playing.call("view.table", group=groups[0]["label"])
    overall = playing.call("view.table")
    assert len(overall) == 12 and all(r["club_name"] for r in overall)
    assert playing.call("view.fixtures", club_id="alvorada")
    february = playing.call("view.calendar", month=2)
    assert len(february) == 28
    assert any(d["user_match"] for d in february)
    assert all({"day", "user_match", "match_count", "windows", "events"} <= set(d)
               for d in february)
    assert playing.error("view.calendar", month=13)["code"] == "NOT_FOUND"
    assert isinstance(playing.call("view.news"), list)
    first = playing.call("view.fixtures", club_id="alvorada")[0]
    unplayed = playing.call("view.match", match_id=first["id"])
    assert unplayed["feed"] == [] and unplayed["stats"] == []


def test_shutdown_saves_and_stops(playing: Client, tmp_path: Path) -> None:
    playing.call("career.continue")
    assert playing.call("shutdown") == {"saved": True}
    assert playing.session.stop
    assert api.load_career(tmp_path, "jogo").current_date.isoformat() == \
        playing.call("career.status")["current_date"]


def test_parity_with_the_facade(tmp_path: Path) -> None:
    """A season through the server, confirming the current selection at each user match, equals
    the same career through the facade (SC-002)."""
    client = Client(tmp_path / "server")
    client.call("career.new", name="par", club_id="serra-negra")
    while True:
        stop = client.call("career.continue")
        if stop["kind"] == "user_match":
            client.call("selection.confirm",
                        selection=client.call("selection.current")["selection"])
        if stop["kind"] == "season_end":
            break
    served = client.session.state["career"]
    world = api.load_dataset(SAMPLE).dataset
    assert world is not None
    direct = api.new_career(world, "par", "serra-negra", master_seed=served.master_seed)
    while True:
        stop = api.continue_career(direct, tmp_path / "direct")
        if stop.kind == "user_match":
            current = direct.selection
            valid = current is not None and not any(
                i.severity == "error" for i in api.validate_selection(direct, current))
            api.confirm_selection(direct, current if valid else api.propose_selection(direct))
        if stop.kind == "season_end":
            break
    assert served.season.results == direct.season.results


def test_the_real_process(tmp_path: Path) -> None:
    """The server as the client starts it: stdio, one line per message, UTF-8."""
    lines = [json.dumps({"jsonrpc": "2.0", "id": 1, "method": "hello",
                         "params": {"client": "test"}}),
             json.dumps({"jsonrpc": "2.0", "id": 2, "method": "shutdown"})]
    done = subprocess.run([sys.executable, "-m", "manager_core.server", "--saves",
                           str(tmp_path)], input="\n".join(lines) + "\n", capture_output=True,
                          text=True, encoding="utf-8", timeout=120, check=True)
    answers = [json.loads(line) for line in done.stdout.splitlines()]
    assert answers[0]["result"]["contract"] == CONTRACT_VERSION
    assert answers[0]["result"]["strings"]["ui.select.title"].startswith("Escalação")
    assert answers[1] == {"jsonrpc": "2.0", "id": 2, "result": {"saved": False}}
