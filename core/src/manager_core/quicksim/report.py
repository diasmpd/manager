"""Match output: events, the stat line and the invariants every match must satisfy
(data-model.md, SC-005)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from manager_core.domain.positions import Position

if TYPE_CHECKING:
    from manager_core.competition.results import Result

HOME = "home"
AWAY = "away"
SIDES = (HOME, AWAY)
HALF_TIME = 46  # half-time substitutions are recorded at minute 46

GOAL_KINDS = frozenset({"goal", "own_goal", "penalty_goal"})
EVENT_KINDS = frozenset({"goal", "own_goal", "penalty_goal", "penalty_miss", "yellow",
                         "second_yellow", "red", "sub"})


def other(side: str) -> str:
    return AWAY if side == HOME else HOME


@dataclass(frozen=True, slots=True, order=True)
class Minute:
    base: int
    added: int = 0

    def __str__(self) -> str:
        return f"{self.base}+{self.added}" if self.added else str(self.base)


@dataclass(frozen=True, slots=True)
class MatchEvent:
    """`side` is the side the event counts for. For an own goal it is the scoring side and
    `player_id` belongs to the other side. For a substitution `player_id` goes off and
    `other_player_id` comes on; for a goal `other_player_id` is the assister."""

    minute: Minute
    side: str
    kind: str
    player_id: str
    other_player_id: str | None = None
    xg: float | None = None


@dataclass(frozen=True, slots=True)
class SideStats:
    goals: int
    shots: int
    shots_on_target: int
    xg: float
    possession: int
    corners: int
    fouls: int
    yellows: int
    reds: int


@dataclass(frozen=True, slots=True)
class SideLineup:
    club_id: str
    formation: str
    starters: tuple[tuple[Position, str], ...]  # slot position, player id
    bench: tuple[str, ...]
    flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ShootoutKick:
    side: str
    player_id: str
    scored: bool


@dataclass(frozen=True, slots=True)
class MatchReport:
    home: SideStats
    away: SideStats
    events: tuple[MatchEvent, ...]
    home_lineup: SideLineup
    away_lineup: SideLineup
    home_finishers: tuple[str, ...]
    away_finishers: tuple[str, ...]
    stoppage: tuple[int, int]
    model_version: str
    shootout_kicks: tuple[ShootoutKick, ...] = field(default=())

    def stats(self, side: str) -> SideStats:
        return self.home if side == HOME else self.away

    def lineup(self, side: str) -> SideLineup:
        return self.home_lineup if side == HOME else self.away_lineup

    def finishers(self, side: str) -> tuple[str, ...]:
        return self.home_finishers if side == HOME else self.away_finishers


def card_counts(events: Sequence[MatchEvent], side: str) -> tuple[int, int]:
    """(yellows, reds) for a side. A second yellow counts as a yellow and a red (R5)."""
    yellows = sum(1 for e in events if e.side == side and e.kind in ("yellow", "second_yellow"))
    reds = sum(1 for e in events if e.side == side and e.kind in ("red", "second_yellow"))
    return yellows, reds


def check_invariants(report: MatchReport, result: Result | None = None) -> list[str]:
    """Every violated invariant, as short codes (empty when the match is consistent)."""
    problems: list[str] = []
    events = report.events
    if any(e.kind not in EVENT_KINDS or e.side not in SIDES for e in events):
        problems.append("unknown_event")
    if list(events) != sorted(events, key=lambda e: e.minute):
        problems.append("events_out_of_order")
    for side in SIDES:
        stats = report.stats(side)
        own_goals_for = sum(1 for e in events if e.side == side and e.kind == "own_goal")
        goals = sum(1 for e in events if e.side == side and e.kind in GOAL_KINDS)
        if goals != stats.goals:
            problems.append(f"goal_events:{side}")
        if not stats.goals - own_goals_for <= stats.shots_on_target <= stats.shots:
            problems.append(f"shot_counts:{side}")
        if card_counts(events, side) != (stats.yellows, stats.reds):
            problems.append(f"card_totals:{side}")
    if report.home.possession + report.away.possession != 100:
        problems.append("possession")
    problems.extend(_check_players(report))
    if result is not None:
        if (result.home_goals, result.away_goals) != (report.home.goals, report.away.goals):
            problems.append("result_goals")
        if ((result.home_yellow, result.home_red, result.away_yellow, result.away_red)
                != (report.home.yellows, report.home.reds, report.away.yellows,
                    report.away.reds)):
            problems.append("result_cards")
    return problems


def _check_players(report: MatchReport) -> list[str]:
    problems: list[str] = []
    on: dict[str, set[str]] = {s: {p for _, p in report.lineup(s).starters} for s in SIDES}
    bench = {s: set(report.lineup(s).bench) for s in SIDES}
    played = {s: set(on[s]) for s in SIDES}
    off: set[str] = set()
    yellows: dict[str, int] = {}
    subs = {s: 0 for s in SIDES}
    windows: dict[str, set[Minute]] = {s: set() for s in SIDES}

    for e in report.events:
        actor_side = other(e.side) if e.kind == "own_goal" else e.side
        if e.player_id not in on[actor_side]:
            problems.append(f"not_on_pitch:{e.kind}:{e.player_id}")
            continue
        if (e.kind in GOAL_KINDS and e.other_player_id is not None
                and (e.other_player_id == e.player_id or e.other_player_id not in on[e.side])):
            problems.append(f"bad_assister:{e.player_id}")
        if e.kind == "yellow":
            yellows[e.player_id] = yellows.get(e.player_id, 0) + 1
            if yellows[e.player_id] > 1:
                problems.append(f"yellow_without_dismissal:{e.player_id}")
        elif e.kind == "second_yellow":
            if yellows.get(e.player_id, 0) != 1:
                problems.append(f"second_yellow_without_first:{e.player_id}")
            on[actor_side].discard(e.player_id)
            off.add(e.player_id)
        elif e.kind == "red":
            on[actor_side].discard(e.player_id)
            off.add(e.player_id)
        elif e.kind == "sub":
            incoming = e.other_player_id
            subs[e.side] += 1
            if e.minute != Minute(HALF_TIME):
                windows[e.side].add(e.minute)
            if incoming is None or incoming not in bench[e.side] or incoming in played[e.side]:
                problems.append(f"bad_sub:{incoming}")
                continue
            on[e.side].discard(e.player_id)
            off.add(e.player_id)
            on[e.side].add(incoming)
            played[e.side].add(incoming)
    for side in SIDES:
        if subs[side] > 5:
            problems.append(f"too_many_subs:{side}")
        if len(windows[side]) > 3:
            problems.append(f"too_many_windows:{side}")
        if set(report.finishers(side)) != on[side]:
            problems.append(f"finishers:{side}")
    return problems
