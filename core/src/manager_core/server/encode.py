"""JSON encoding for the local API contract (spec 007, contracts/local-api.md).

Results are plain JSON: a dataclass becomes an object with its field names, an enum its value, a
date an ISO string, and tuples, lists and sets arrays. Decoders turn the client's JSON back into
the facade's inputs (a selection and a tactic), the reverse of `to_json` for those types.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any

from manager_core.career.selection import Selection
from manager_core.tactics.model import SetPieces, SlotTactic, Tactic

Json = Any


def to_json(value: object) -> Json:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date | datetime):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(to_json(k)): to_json(v) for k, v in value.items()}
    if isinstance(value, set | frozenset):
        return sorted((to_json(v) for v in value), key=repr)
    if isinstance(value, list | tuple):
        return [to_json(v) for v in value]
    raise TypeError(f"cannot encode {type(value).__name__}")


class DecodeError(ValueError):
    """The client sent a value of the wrong shape (a P003 error)."""


def _pairs(raw: Json, name: str) -> tuple[tuple[Any, Any], ...]:
    if not isinstance(raw, list) or not all(isinstance(p, list) and len(p) == 2 for p in raw):
        raise DecodeError(name)
    return tuple((a, b) for a, b in raw)


def selection_from_json(raw: Json) -> Selection:
    try:
        starters = tuple((int(slot), str(pid)) for slot, pid in _pairs(raw["starters"],
                                                                      "starters"))
        return Selection(str(raw["formation"]), starters, tuple(str(p) for p in raw["bench"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise DecodeError("selection") from exc


def tactic_from_json(raw: Json) -> Tactic:
    try:
        slots = tuple(SlotTactic(int(s["slot"]), str(s["ip_role"]), str(s["oop_role"]),
                                 _pairs(s.get("instructions", []), "instructions"))
                      for s in raw["slots"])
        set_pieces = raw.get("set_pieces", {})
        return Tactic(str(raw["ip_formation"]), str(raw["oop_formation"]), str(raw["mentality"]),
                      _pairs(raw["team"], "team"), slots,
                      SetPieces(_pairs(set_pieces.get("takers", []), "takers"),
                                _pairs(set_pieces.get("setups", []), "setups")),
                      raw.get("style"))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DecodeError("tactic") from exc
