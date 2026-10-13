"""What a view needs to draw a positional match besides the record (spec 008b): the kits, with
the colour-clash rule, the shirt numbers and the line-ups. Every choice here is deterministic
and lives in the core, so no client holds a rule (Constitution III). The constants are data in
`reference/match_view.toml`."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset
from manager_core.positional import pitch
from manager_core.positional.record import SLOTS

HOME_SLOTS = SLOTS // 2


@cache
def view_data() -> Mapping[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("match_view.toml")
    return tomllib.loads(entry.read_text("utf-8"))


@dataclass(frozen=True, slots=True)
class Kit:
    shirt: str  # #RRGGBB
    number: str
    keeper: str


@dataclass(frozen=True, slots=True)
class PitchPlayer:
    slot: int  # the record's 0-21; -1 on the bench
    player_id: str
    name: str
    number: int
    keeper: bool


@dataclass(frozen=True, slots=True)
class PitchSide:
    club_id: str
    name: str
    kit: Kit
    players: tuple[PitchPlayer, ...]  # the starters, in slot order
    bench: tuple[PitchPlayer, ...]


@dataclass(frozen=True, slots=True)
class PitchView:
    length_cm: int
    width_cm: int
    hz: float
    home: PitchSide
    away: PitchSide


def _rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def distance(a: str, b: str) -> float:
    """How far apart two colours are (0-441)."""
    return float(sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b), strict=True)) ** 0.5)


def _number_colour(shirt: str) -> str:
    r, g, b = _rgb(shirt)
    return "#111111" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#FFFFFF"


def _first_clear(candidates: Sequence[str], against: Sequence[str], clash: float) -> str:
    """The first candidate that clashes with none of `against`; failing that, the one farthest
    from its nearest (the first of them on a tie)."""
    for colour in candidates:
        if all(distance(colour, other) >= clash for other in against):
            return colour
    return max(candidates, key=lambda c: min(distance(c, other) for other in against))


def kits(home: Club, away: Club) -> tuple[Kit, Kit]:
    """The home side plays in its colours. The away side changes to its second colour, and
    then to a neutral kit, when its shirt would clash with the home one."""
    data = view_data()["kits"]
    clash = float(data["clash_distance"])
    home_shirt = home.color_primary.upper()
    away_shirt = _first_clear(
        [away.color_primary.upper(), away.color_secondary.upper(), *data["neutral"]],
        [home_shirt], clash)
    home_keeper = _first_clear(data["keepers"], [home_shirt, away_shirt], clash)
    away_keeper = _first_clear(data["keepers"], [home_shirt, away_shirt, home_keeper], clash)
    return (Kit(home_shirt, _number_colour(home_shirt), home_keeper),
            Kit(away_shirt, _number_colour(away_shirt), away_keeper))


def numbers(dataset: Dataset, starters: Sequence[str], others: Sequence[str]) -> dict[str, int]:
    """Shirt numbers for one side: the dataset's when every player has one and none repeats;
    otherwise 1-11 by slot and 12 onwards for the others, in their order."""
    everyone = [*starters, *others]
    own = [m.shirt_number if (m := dataset.memberships.get(pid)) else None for pid in everyone]
    if all(n is not None for n in own) and len(set(own)) == len(own):
        return {pid: int(n) for pid, n in zip(everyone, own, strict=True) if n is not None}
    return {pid: i for i, pid in enumerate(everyone, start=1)}


def _side(dataset: Dataset, club: Club, kit: Kit, first_slot: int, starters: Sequence[str],
          others: Sequence[str], keeper: int) -> PitchSide:
    shirt = numbers(dataset, starters, others)

    def player(slot: int, pid: str) -> PitchPlayer:
        return PitchPlayer(slot, pid, dataset.players[pid].display_name, shirt[pid],
                           slot == first_slot + keeper)

    return PitchSide(club.id, club.short_name, kit,
                     tuple(player(first_slot + i, pid) for i, pid in enumerate(starters)),
                     tuple(player(-1, pid) for pid in others))


def pitch_view(dataset: Dataset, hz: float, home_id: str, away_id: str,
               starters: tuple[Sequence[str], Sequence[str]],
               others: tuple[Sequence[str], Sequence[str]],
               keepers: tuple[int, int]) -> PitchView:
    """`starters` are each side's eleven in slot order, `others` whoever else may come on, and
    `keepers` each side's goalkeeper slot (0-10)."""
    home, away = dataset.club(home_id), dataset.club(away_id)
    home_kit, away_kit = kits(home, away)
    return PitchView(
        round(pitch.LENGTH * 100), round(pitch.WIDTH * 100), hz,
        _side(dataset, home, home_kit, 0, starters[0], others[0], keepers[0]),
        _side(dataset, away, away_kit, HOME_SLOTS, starters[1], others[1], keepers[1]))


def highlight_samples(kinds: Sequence[tuple[int, str]],
                      shots: Sequence[tuple[int, int, bool]]) -> list[int]:
    """The samples of a match's highlights: `kinds` are its events as (sample, kind), `shots`
    the record's shot marks. Which kinds count is data."""
    wanted = set(view_data()["highlights"]["kinds"])
    found = {sample for sample, kind in kinds if kind in wanted}
    if "shot_on_target" in wanted:
        found |= {sample for sample, _, on_target in shots if on_target}
    return sorted(found)


def passages(samples: Sequence[int], hz: float) -> tuple[tuple[float, float], ...]:
    """The passages of play a highlights view shows, in match seconds: from some seconds before
    each highlight to just after it, joined when two are close together."""
    data = view_data()["highlights"]
    lead_in, lead_out, gap = (float(data[k]) for k in ("lead_in_s", "lead_out_s", "merge_gap_s"))
    spans: list[tuple[float, float]] = []
    for sample in sorted(samples):
        start, end = max(0.0, sample / hz - lead_in), sample / hz + lead_out
        if spans and start - spans[-1][1] <= gap:
            spans[-1] = (spans[-1][0], max(spans[-1][1], end))
        else:
            spans.append((start, end))
    return tuple(spans)


def second_half_sample(samples: Sequence[Sequence[int]], length_cm: int) -> int | None:
    """The first sample of the second half: the sides change ends, so the home goalkeeper is
    suddenly in the other half. None for a record that stops before half-time."""
    if not samples:
        return None
    index = 3 + 2 * keepers_at_kick_off(samples[0])[0]
    for i, sample in enumerate(samples):
        if sample[index] > length_cm / 2:
            return i
    return None


def clock(count: int, hz: float, second_half: int | None) -> tuple[tuple[int, int, int], ...]:
    """The match clock of a record: (sample, minute, added) at every change of minute, as the
    scoreboard shows it (45+2, 90+4)."""
    rows: list[tuple[int, int, int]] = []
    per_minute = 60 * hz
    for sample in range(count):
        if second_half is None or sample < second_half:
            minute, end = int(sample // per_minute) + 1, 45
        else:
            minute, end = int((sample - second_half) // per_minute) + 46, 90
        row = (min(minute, end), max(0, minute - end))
        if not rows or rows[-1][1:] != row:
            rows.append((sample, *row))
    return tuple(rows)


def keepers_at_kick_off(sample: Sequence[int]) -> tuple[int, int]:
    """Each side's goalkeeper slot (0-10) from a record's first sample: the player nearest his
    own goal line. The home side defends x = 0 in the first half."""
    xs = [sample[3 + 2 * slot] for slot in range(SLOTS)]
    home = min(range(HOME_SLOTS), key=lambda i: (xs[i], i))
    away = max(range(HOME_SLOTS), key=lambda i: (xs[HOME_SLOTS + i], -i))
    return home, away
