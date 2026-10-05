"""The positional record (spec 008 FR-004, research R8): every player's and the ball's positions
at 2 Hz, in centimetres as int16, zlib-compressed. A 2D or 3D view replays it without the
engine (Constitution III)."""

from __future__ import annotations

import array
import json
import zlib
from dataclasses import dataclass

OFF_PITCH = -1
SLOTS = 22  # home 0-10, away 11-21 (the players' ids are in `players`)


@dataclass(frozen=True)
class PositionalRecord:
    hz: float
    players: tuple[tuple[str, str], ...]  # (player id, side) in sample order, per slot
    samples: tuple[tuple[int, ...], ...]  # ball x, y, z, then 22 (x, y), centimetres
    events: tuple[tuple[int, int], ...]  # (sample index, event index in the match report)
    subs: tuple[tuple[int, int, str], ...] = ()  # (sample index, slot, incoming player id)

    def encode(self) -> bytes:
        header = json.dumps(
            {
                "hz": self.hz,
                "players": self.players,
                "events": self.events,
                "subs": self.subs,
                "count": len(self.samples),
            }
        ).encode("utf-8")
        body = array.array("h", [value for sample in self.samples for value in sample])
        return zlib.compress(len(header).to_bytes(4, "little") + header + body.tobytes(), 6)

    @staticmethod
    def decode(blob: bytes) -> PositionalRecord:
        raw = zlib.decompress(blob)
        size = int.from_bytes(raw[:4], "little")
        header = json.loads(raw[4 : 4 + size].decode("utf-8"))
        values = array.array("h")
        values.frombytes(raw[4 + size :])
        width = 3 + 2 * SLOTS
        samples = tuple(tuple(values[i : i + width]) for i in range(0, len(values), width))
        return PositionalRecord(
            header["hz"],
            tuple((p, s) for p, s in header["players"]),
            samples,
            tuple((a, b) for a, b in header["events"]),
            tuple((a, b, c) for a, b, c in header["subs"]),
        )


def to_cm(value: float) -> int:
    return max(-32768, min(32767, round(value * 100)))
