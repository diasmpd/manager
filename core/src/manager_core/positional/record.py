"""The positional record (spec 008 FR-004, research R8): every player's and the ball's positions
at 2 Hz, in centimetres as int16, zlib-compressed. A 2D or 3D view replays it without the
engine (Constitution III)."""

from __future__ import annotations

import array
import base64
import json
import sys
import zlib
from dataclasses import dataclass

OFF_PITCH = -1
SLOTS = 22  # home 0-10, away 11-21 (the players' ids are in `players`)
WIDTH = 3 + 2 * SLOTS  # values in a sample


def samples_base64(samples: tuple[tuple[int, ...], ...]) -> str:
    """Samples for the local API (spec 008b, research R3): their int16 values, little-endian,
    in base64."""
    body = array.array("h", [value for sample in samples for value in sample])
    if sys.byteorder == "big":
        body.byteswap()
    return base64.b64encode(body.tobytes()).decode("ascii")


@dataclass(frozen=True)
class RecordChunk:
    """A part of a record, with the indices of the whole (spec 008b): what a live match has
    played since the last chunk, or a whole stored record."""

    first: int  # the index of the first sample
    samples: tuple[tuple[int, ...], ...]
    events: tuple[tuple[int, int], ...]
    subs: tuple[tuple[int, int, str], ...]
    shots: tuple[tuple[int, int, bool], ...]


@dataclass(frozen=True)
class PositionalRecord:
    hz: float
    players: tuple[tuple[str, str], ...]  # (player id, side) in sample order, per slot
    samples: tuple[tuple[int, ...], ...]  # ball x, y, z, then 22 (x, y), centimetres
    events: tuple[tuple[int, int], ...]  # (sample index, event index in the match report)
    subs: tuple[tuple[int, int, str], ...] = ()  # (sample index, slot, incoming player id)
    # (sample index, the shooter's slot, on target): spec 008b; older records have none
    shots: tuple[tuple[int, int, bool], ...] = ()

    def chunk(self) -> RecordChunk:
        return RecordChunk(0, self.samples, self.events, self.subs, self.shots)

    def encode(self) -> bytes:
        header = json.dumps(
            {
                "hz": self.hz,
                "players": self.players,
                "events": self.events,
                "subs": self.subs,
                "shots": self.shots,
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
        samples = tuple(tuple(values[i : i + WIDTH]) for i in range(0, len(values), WIDTH))
        return PositionalRecord(
            header["hz"],
            tuple((p, s) for p, s in header["players"]),
            samples,
            tuple((a, b) for a, b in header["events"]),
            tuple((a, b, c) for a, b, c in header["subs"]),
            tuple((a, b, bool(c)) for a, b, c in header.get("shots", ())),
        )


def to_cm(value: float) -> int:
    return max(-32768, min(32767, round(value * 100)))
