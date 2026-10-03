"""Deterministic seeds (research R4).

Python's hash() is randomised per process, so seeds come from SHA-256. Every random decision
(the draw, each match, each drawing of lots) gets its own sub-seed from a stable label, so a
match's result does not depend on the order matches are simulated in.
"""

from __future__ import annotations

import hashlib


def _digest(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def season_seed(master_seed: int, year: int) -> int:
    return _digest(f"season:{master_seed}:{year}")


def sub_seed(seed: int, label: str) -> int:
    return _digest(f"{seed}:{label}")
