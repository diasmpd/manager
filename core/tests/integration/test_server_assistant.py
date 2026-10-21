"""The assistant over the local API (spec 010 T012): the briefing, and every action applied
through the existing methods, as the client does."""

from __future__ import annotations

from pathlib import Path

from .test_server_methods import Client


def test_the_briefing_and_its_actions(tmp_path: Path) -> None:
    client = Client(tmp_path)
    client.call("career.new", name="assistente", club_id="alvorada")
    briefing = client.call("assistant.briefing")
    assert briefing["report"]["opponent_name"] and briefing["report"]["text"]
    assert set(briefing) == {"report", "selection", "tactic", "squad"}
    for advice in briefing["selection"] + briefing["tactic"] + briefing["squad"]:
        assert advice["severity"] in ("info", "warning") and advice["text"]
    actions = [a["action"] for a in briefing["tactic"] if a["action"]]
    assert actions, "the sample's first match has a tactic suggestion"
    for action in actions:
        tactic = client.call("tactic.current")
        if action["type"] == "role":
            tactic = client.call("tactic.set_role", tactic=tactic, slot=action["slot"],
                                 phase=action["phase"], role_id=action["role_id"])
        else:
            assert action["type"] == "tactic"
            tactic = action["tactic"]
        assert client.call("tactic.validate", tactic=tactic) == []
        client.call("tactic.confirm", tactic=tactic)
    after = client.call("tactic.current")
    if any(a["type"] == "tactic" for a in actions):
        adapted = next(a["tactic"] for a in actions if a["type"] == "tactic")
        assert after["mentality"] == adapted["mentality"]


def test_a_swap_action_through_the_selection_methods(tmp_path: Path) -> None:
    client = Client(tmp_path)
    client.call("career.new", name="troca", club_id="alvorada")
    current = client.call("selection.current")
    selection = current["selection"]
    # put a reserve who is not a striker up front: the assistant suggests the fix
    positions = current["positions"]
    striker = positions.index("ST")
    in_xi = {pid for _, pid in selection["starters"]} | set(selection["bench"])
    reserve = next(r["player_id"] for r in current["squad"]
                   if r["player_id"] not in in_xi and r["position"] not in ("ST", "GK"))
    misplaced = client.call("selection.swap", selection=selection, slot=striker,
                            player_id=reserve)
    # the selection on screen, not kept yet, is the one advised on
    shown = [a for a in client.call("assistant.briefing", selection=misplaced)["selection"]
             if a["kind"] == "out_of_position"]
    assert shown
    assert not [a for a in client.call("assistant.briefing")["selection"]
                if a["kind"] == "out_of_position"]
    client.call("selection.confirm", selection=misplaced)
    advice = [a for a in client.call("assistant.briefing")["selection"]
              if a["kind"] == "out_of_position"]
    assert advice and advice[0]["action"]["type"] == "swap"
    action = advice[0]["action"]
    fixed = client.call("selection.swap", selection=misplaced, slot=action["slot"],
                        player_id=action["player_id"])
    client.call("selection.confirm", selection=fixed)
    assert not [a for a in client.call("assistant.briefing")["selection"]
                if a["kind"] == "out_of_position"]
