"""The local API's encoding and wire protocol (spec 007 T003, T004)."""

import io
import json
from dataclasses import dataclass
from datetime import date
from enum import Enum

import pytest

from manager_core.career.selection import Selection
from manager_core.server.encode import (
    DecodeError,
    selection_from_json,
    tactic_from_json,
    to_json,
)
from manager_core.server.protocol import RpcError, Session, handle_line, param, serve
from manager_core.tactics.model import default_tactic


class Colour(Enum):
    RED = "red"


@dataclass(frozen=True)
class Inner:
    when: date
    colour: Colour


@dataclass(frozen=True)
class Outer:
    name: str
    items: tuple[Inner, ...]
    tags: frozenset[str]
    scores: dict[str, float]
    nothing: None = None


def test_to_json_handles_the_core_types() -> None:
    value = Outer("x", (Inner(date(2027, 1, 2), Colour.RED),), frozenset({"b", "a"}),
                  {"k": 1.5})
    assert to_json(value) == {"name": "x", "items": [{"when": "2027-01-02", "colour": "red"}],
                              "tags": ["a", "b"], "scores": {"k": 1.5}, "nothing": None}
    with pytest.raises(TypeError):
        to_json(object())


def test_selection_and_tactic_round_trip() -> None:
    selection = Selection("4-4-2", ((0, "p1"), (1, "p2")), ("p3",))
    assert selection_from_json(to_json(selection)) == selection
    tactic = default_tactic("4-3-3")
    assert tactic_from_json(json.loads(json.dumps(to_json(tactic)))) == tactic
    with pytest.raises(DecodeError):
        selection_from_json({"formation": "4-4-2"})
    with pytest.raises(DecodeError):
        tactic_from_json({"ip_formation": "4-4-2"})


def _run(methods: dict, *lines: str) -> list[dict]:
    out = io.StringIO()
    session = Session(out)
    serve(session, methods, lines)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def _echo(s: Session, p: dict) -> object:
    x = param(p, "x", int)
    s.notify("progress", {"step": 1})
    return {"got": x}


def test_one_answer_per_request_in_order() -> None:
    answers = _run({"echo": _echo},
                   '{"jsonrpc":"2.0","id":1,"method":"echo","params":{"x":5}}\n',
                   "\n",  # blank lines are ignored
                   '{"jsonrpc":"2.0","id":2,"method":"echo","params":{"x":6}}\n')
    assert answers[0] == {"jsonrpc": "2.0", "method": "progress",
                          "params": {"request": 1, "step": 1}}
    assert answers[1] == {"jsonrpc": "2.0", "id": 1, "result": {"got": 5}}
    assert answers[3]["result"] == {"got": 6}


@pytest.mark.parametrize(("line", "code"), [
    ("not json", "P001"),
    ('["a list"]', "P001"),
    ('{"id":1,"method":"nope"}', "P002"),
    ('{"id":1,"method":"echo","params":[]}', "P003"),
    ('{"id":1,"method":"echo","params":{}}', "P003"),
    ('{"id":1,"method":"echo","params":{"x":"5"}}', "P003"),
    ('{"id":1,"method":"echo","params":{"x":true}}', "P003"),
    ('{"id":1,"method":"boom"}', "P005"),
])
def test_errors_are_answers_and_the_server_keeps_going(line: str, code: str) -> None:
    def boom(s: Session, p: dict) -> object:
        raise RuntimeError("kaput")

    answers = _run({"echo": _echo, "boom": boom}, line,
                   '{"id":9,"method":"echo","params":{"x":1}}')
    error = answers[0]["error"]
    assert error["code"] == code and error["message"]
    assert answers[-1]["result"] == {"got": 1}


def test_a_handler_error_keeps_its_code_and_data() -> None:
    def refuse(s: Session, p: dict) -> object:
        raise RpcError("SELECTION", "Escalação inválida", {"issues": [{"code": "suspended"}]})

    out = io.StringIO()
    handle_line(Session(out), {"refuse": refuse}, '{"id":3,"method":"refuse"}')
    answer = json.loads(out.getvalue())
    assert answer == {"jsonrpc": "2.0", "id": 3, "error": {
        "code": "SELECTION", "message": "Escalação inválida",
        "data": {"issues": [{"code": "suspended"}]}}}


def test_stop_ends_the_loop_after_the_answer() -> None:
    def bye(s: Session, p: dict) -> object:
        s.stop = True
        return {}

    answers = _run({"bye": bye, "echo": _echo}, '{"id":1,"method":"bye"}',
                   '{"id":2,"method":"echo","params":{"x":1}}')
    assert answers == [{"jsonrpc": "2.0", "id": 1, "result": {}}]


def test_messages_are_one_line_utf8() -> None:
    def text(s: Session, p: dict) -> object:
        return {"t": "Escalação\nconfirmada"}

    out = io.StringIO()
    handle_line(Session(out), {"text": text}, '{"id":1,"method":"text"}')
    assert out.getvalue().count("\n") == 1
    assert "Escalação" in out.getvalue()
