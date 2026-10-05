"""The positional engine's match loop (spec 008): `LiveMatch` steps 22 players and the ball at
4 Hz. Off the ball players run to their tactical spots; the ball carrier decides among passes,
dribbles, shots, crosses and clearances; pressers duel for the ball, sometimes fouling.

The report is the quick sim's `MatchReport`, so feeds, news, discipline and tables work
unchanged. The record samples every position at 2 Hz for a 2D view. Given its seed and the
recorded decisions, a match replays exactly (Constitution II).
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from manager_core.competition.results import Result
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.positional import pitch
from manager_core.positional.params import PositionalParams
from manager_core.positional.record import OFF_PITCH, SLOTS, PositionalRecord, to_cm
from manager_core.quicksim.engine import caution_strength, kick_factor, penalty_taker
from manager_core.quicksim.params import ModelParams
from manager_core.quicksim.ratings import POSITION_GROUP, Group, discipline_score
from manager_core.quicksim.report import (
    AWAY,
    HOME,
    MatchEvent,
    MatchReport,
    Minute,
    SideLineup,
    SideStats,
    TacticSummary,
    card_counts,
    other,
)
from manager_core.quicksim.squad import TeamSheet
from manager_core.tactics.model import Tactic, default_tactic, for_formation, tactic_digest

SOURCE = "positional"
HALF_S = 45 * 60


_ATTRS: dict[str, dict[str, float]] = {}


def _attributes(player: Player) -> dict[str, float]:
    """Every attribute of a player as floats, cached per player id."""
    cached = _ATTRS.get(player.id)
    if cached is None:
        from manager_core.domain.attributes import ALL_ATTRIBUTES

        cached = {name: float(player.attributes.get(name)) for name in ALL_ATTRIBUTES}
        _ATTRS[player.id] = cached
    return cached


@dataclass
class Body:
    """A player on (or off) the pitch, in absolute coordinates."""

    pid: str
    side: str
    slot: int
    player: Player
    position: Position
    x: float = 0.0
    y: float = 0.0
    tx: float = 0.0
    ty: float = 0.0
    energy: float = 1.0
    yellow: bool = False
    on: bool = True
    distance: float = 0.0
    sprint: float = 0.0
    attrs: dict[str, float] = field(default_factory=dict)
    base_speed: float = 7.5
    stamina: float = 0.5

    def __post_init__(self) -> None:
        if not self.attrs:
            self.attrs = _attributes(self.player)
        self.stamina = max(0.25, (self.attr("stamina") + self.attr("natural_fitness")) / 40)

    @property
    def group(self) -> Group:
        return POSITION_GROUP[self.position]

    def attr(self, name: str) -> float:
        return self.attrs.get(name, 10.0)


@dataclass
class Team:
    side: str
    sheet: TeamSheet
    tactic: Tactic
    start_mentality: str
    bodies: list[Body] = field(default_factory=list)
    bench: list[str] = field(default_factory=list)
    goals: int = 0
    shots: int = 0
    on_target: int = 0
    xg: float = 0.0
    corners: int = 0
    fouls: int = 0
    subs: int = 0
    windows: int = 0
    came_on: set[str] = field(default_factory=set)
    played: set[str] = field(default_factory=set)
    owned_s: float = 0.0

    def on_pitch(self) -> list[Body]:
        return [b for b in self.bodies if b.on]

    def keeper(self) -> Body | None:
        return next((b for b in self.bodies if b.on and b.group is Group.GOALKEEPER), None)


@dataclass(frozen=True)
class Decision:
    """A user decision during a live match (data-model.md), applied before the step at `at`."""

    at: float
    side: str
    kind: str  # substitution / tactic
    off: str | None = None
    on: str | None = None
    tactic: Tactic | None = None


@dataclass
class Ball:
    x: float = pitch.LENGTH / 2
    y: float = pitch.CENTRE_V
    owner: Body | None = None
    # a ball in flight: where it lands, when, and what happens there
    flight: tuple[float, float, float] | None = None  # target x, y, arrival time
    landing: str = ""  # receive / intercept / shot / out
    receiver: Body | None = None
    shot_xg: float = 0.0
    shooter: Body | None = None
    passer: Body | None = None


class LiveMatch:
    """A match that can be stepped, paused (by not stepping) and changed (`apply`)."""

    def __init__(
        self,
        home: TeamSheet,
        away: TeamSheet,
        players: Mapping[str, Player],
        params: PositionalParams,
        qparams: ModelParams,
        rng: random.Random,
        neutral: bool = False,
        home_tactic: Tactic | None = None,
        away_tactic: Tactic | None = None,
        record: bool = True,
    ) -> None:
        self.p = params
        self.q = qparams
        self.pm = dict(params["movement"])
        self.pe = dict(params["energy"])
        self.pd = dict(params["decide"])
        self.ps = dict(params["shape"])
        self.px = dict(params["xg"])
        self.pdu = dict(params["duel"])
        edge = 0.0 if neutral else params["home"]["edge"]
        self.edge = {HOME: edge, AWAY: -edge}
        self.rng = rng
        self.neutral = neutral
        self.players = players
        self.events: list[MatchEvent] = []
        self.feed_index = 0
        self.teams = {
            HOME: self._team(HOME, home, home_tactic),
            AWAY: self._team(AWAY, away, away_tactic),
        }
        self.t = 0.0
        self.half = 1
        self.stoppage = (
            self.rng.randint(*qparams.stoppage.first),
            self.rng.randint(*qparams.stoppage.second),
        )
        self.ball = Ball()
        self.finished = False
        self.recording = record
        self.samples: list[tuple[int, ...]] = []
        self.event_samples: list[tuple[int, int]] = []
        self.sub_samples: list[tuple[int, int, str]] = []
        self.decisions: list[Decision] = []
        self._pending: list[Decision] = []
        self._next_decision = 0.0
        self._next_targets = 0.0
        self._duel_clock = 0.0
        self.dead_until = 0.0  # a dead ball: the clock runs, nobody plays (restarts, goals)
        self.pr = dict(params["restarts"])
        self._steps = 0
        self.passes = 0  # attempted passes (realism diagnostics and the tuner)
        self.passes_completed = 0
        self._last_toucher: Body | None = None
        self._last_window: dict[str, float] = {HOME: -1.0, AWAY: -1.0}
        self._windows_plan = {s: self._plan_subs() for s in (HOME, AWAY)}
        self._kickoff(HOME)

    # ---- set-up --------------------------------------------------------------------------------

    def _team(self, side: str, sheet: TeamSheet, tactic: Tactic | None) -> Team:
        formation = sheet.formation.name
        fitted = (
            default_tactic(formation) if tactic is None else for_formation(tactic, formation)[0]
        )
        team = Team(side, sheet, fitted, fitted.mentality, bench=list(sheet.bench))
        for slot, pid in sheet.starters:
            body = Body(pid, side, slot, self.players[pid], sheet.slot_position(slot))
            body.base_speed = self._base_speed(body)
            team.bodies.append(body)
            team.played.add(pid)
        return team

    def attacks_positive(self, side: str) -> bool:
        """Home attacks +x in the first half; ends switch at half-time."""
        return (side == HOME) == (self.half == 1)

    def rel(self, side: str, x: float, y: float) -> tuple[float, float]:
        """Absolute -> the side's (u, v)."""
        return (x, y) if self.attacks_positive(side) else (pitch.LENGTH - x, pitch.WIDTH - y)

    def absolute(self, side: str, u: float, v: float) -> tuple[float, float]:
        return pitch.to_absolute(u, v, self.attacks_positive(side))

    def _slot_uv(self, team: Team, body: Body, phase: str) -> tuple[float, float]:
        formation = (
            team.sheet.formation
            if phase == "ip"
            else _formation(team.tactic.oop_formation, team.sheet)
        )
        slots = formation.slots
        slot = slots[body.slot] if body.slot < len(slots) else slots[-1]
        return slot.x_m, slot.y_m

    def _kickoff(self, side: str) -> None:
        for team in self.teams.values():
            for body in team.on_pitch():
                u, v = self._slot_uv(team, body, "oop" if team.side != side else "ip")
                u = min(u * 0.48, pitch.LENGTH / 2 - 1)  # own half
                body.x, body.y = self.absolute(team.side, u, v)
                body.tx, body.ty = body.x, body.y
        kicker = self._nearest(self.teams[side], pitch.LENGTH / 2, pitch.CENTRE_V, outfield=True)
        if kicker is not None:
            kicker.x, kicker.y = pitch.LENGTH / 2, pitch.CENTRE_V
            self._restart(kicker, "kick_off")

    def _plan_subs(self) -> dict[int, int]:
        """The assistant's substitution windows (minute -> count), as the quick sim's."""
        q = self.q.subs
        plan: dict[int, int] = {}
        for lo, hi in q.windows:
            minute = self.rng.randint(lo, hi)
            if self.rng.random() < q.window_chance:
                plan[minute] = plan.get(minute, 0) + self.rng.randint(*q.per_window)
        return plan

    # ---- the clock -----------------------------------------------------------------------------

    def minute(self) -> Minute:
        if self.half == 1:
            m = int(self.t // 60) + 1
            return Minute(45, m - 45) if m > 45 else Minute(m)
        m = int((self.t - HALF_S - self.stoppage[0] * 60) // 60) + 46
        return Minute(90, m - 90) if m > 90 else Minute(m)

    def _half_end(self) -> float:
        if self.half == 1:
            return HALF_S + self.stoppage[0] * 60
        return 2 * HALF_S + (self.stoppage[0] + self.stoppage[1]) * 60

    def at_half_time(self) -> bool:
        """Paused at the end of the first half (before the second half's kick-off)."""
        return self.half == 1 and self.t >= self._half_end()

    def sent_off(self, pid: str) -> bool:
        return any(e.player_id == pid and e.kind in ("red", "second_yellow") for e in self.events)

    def apply(self, decision: Decision) -> None:
        """A user decision, acting from the current moment (the pause): applied at once, before
        the next step, so a replay that applies it at the same match time is identical."""
        self._apply(decision)

    def advance(self, seconds: float) -> None:
        """Play up to `seconds` of match time (or to full time)."""
        end = self.t + seconds
        step = self.p["time"]["step_s"]
        while not self.finished and self.t < end - 1e-9:
            self._step(step)

    def play(self) -> None:
        while not self.finished:
            self._step(self.p["time"]["step_s"])

    def _step(self, dt: float) -> None:
        for decision in self._pending:
            self._apply(decision)
        self._pending.clear()
        if self.t >= self._half_end():
            if self.half == 1:
                self.half = 2
                self._halftime_subs()
                self._kickoff(AWAY)
            else:
                self.finished = True
                return
        minute = self.minute()
        if minute.added == 0 and int(self.t) % 60 == 0 and abs(self.t - round(self.t)) < 1e-9:
            self._assistant_subs(minute.base)
        if self.t >= self._next_targets:
            self._targets()
            self._next_targets = self.t + self.p["time"]["target_every_s"]
        live = self.t >= self.dead_until
        if live:
            self._ball(dt)
        self._move(dt)
        if live and self.ball.owner is not None:
            self.teams[self.ball.owner.side].owned_s += dt
            self._duels(dt)
            if self.ball.owner is not None and self.t >= self._next_decision:
                self._decide(self.ball.owner)
        if self.recording and self._steps % int(self.p["time"]["record_every_steps"]) == 0:
            self._sample()
        self._steps += 1
        self.t += dt

    # ---- shape and movement -----------------------------------------------------------------

    def _intent(self, team: Team) -> str:
        opp = self.teams[other(team.side)]
        diff = team.goals - opp.goals
        late = self.minute().base >= 70
        if diff >= 2:
            return "relaxed"
        if diff < 0 and late:
            return "chase"
        if diff == 1 and late:
            return "protect"
        if diff == 0 and late:
            return "level"
        return "normal"

    def _line_offset(self, team: Team) -> float:
        s = self.p["shape"]
        setting = team.tactic.setting("defensive_line")
        offset = s.get(f"line_{setting}", 0.0)
        mentality_index = _mentality_index(team.tactic.mentality)
        offset += (mentality_index - 3) * 1.5
        intent = self._intent(team)
        if intent == "chase":
            offset += self.p["intents"]["chase_push"]
        elif intent == "protect":
            offset -= self.p["intents"]["protect_drop"]
        return offset

    def _width(self, team: Team, phase: str) -> float:
        s = self.p["shape"]
        base = s["width_ip"] if phase == "ip" else s["width_oop"]
        setting = team.tactic.setting("attacking_width") if phase == "ip" else "standard"
        return base * {
            "much_narrower": 0.8,
            "narrower": 0.9,
            "standard": 1.0,
            "wider": 1.08,
            "much_wider": 1.15,
        }.get(setting, 1.0)

    def _targets(self) -> None:
        owner = self.ball.owner
        for team in self.teams.values():
            in_possession = owner is not None and owner.side == team.side
            phase = "ip" if in_possession else "oop"
            bu, bv = self.rel(team.side, self.ball.x, self.ball.y)
            s = self.p["shape"]
            push = s["ip_push"] if in_possession else s["oop_push"]
            offset = self._line_offset(team)
            width = self._width(team, phase)
            onside = self.offside_line(team.side) - 0.5 if in_possession else pitch.LENGTH
            # out of possession the lines close up towards the defensive line (a compact block)
            back = min(
                (self._slot_uv(team, b, phase)[0] for b in team.on_pitch()
                 if b.group is not Group.GOALKEEPER),
                default=25.0,
            )
            compact = 1.0 if in_possession else s["oop_compact"]
            for body in team.on_pitch():
                if body is owner:
                    continue
                u, v = self._slot_uv(team, body, phase)
                if body.group is Group.GOALKEEPER:
                    tu = min(18.0, 4.0 + max(0.0, bu - 40) * 0.12)
                    tv = pitch.CENTRE_V + (bv - pitch.CENTRE_V) * 0.2
                else:
                    u = back + (u - back) * compact
                    tu = u + (bu - 52.5) * push + offset
                    if in_possession and body.group in (Group.FORWARD, Group.ATTACKING_MID):
                        tu = max(tu, bu - 5)
                    tu = min(tu, onside)
                    tv = pitch.CENTRE_V + (v - pitch.CENTRE_V) * width
                    tv += (bv - pitch.CENTRE_V) * s["lateral_shift"]
                tu, tv = pitch.clamp_point(tu, tv)
                body.tx, body.ty = self.absolute(team.side, tu, tv)
            if not in_possession and owner is not None:
                self._press_targets(team, owner)

    def _press_targets(self, team: Team, carrier: Body) -> None:
        cu, _ = self.rel(team.side, carrier.x, carrier.y)
        own_u = pitch.LENGTH - cu  # distance of the ball from this team's own goal, in its view
        setting = team.tactic.setting("line_of_engagement")
        engage = self.p["shape"].get(f"engage_{setting}", 55.0)
        if pitch.LENGTH - own_u > engage:
            return
        pressers = 2 if team.tactic.setting("trigger_press") == "more_often" else 1
        if cu <= pitch.BOX_DEPTH + 4:  # the carrier is at our box (our view): converge
            pressers = int(self.ps["box_pressers"])
        candidates = sorted(
            (b for b in team.on_pitch() if b.group is not Group.GOALKEEPER),
            key=lambda b: (math.hypot(b.x - carrier.x, b.y - carrier.y), b.pid),
        )
        gu, gv = self.rel(team.side, carrier.x, carrier.y)  # carrier in the defenders' view
        side_u, side_v = pitch.clamp_point(gu - 1.5, gv + (pitch.CENTRE_V - gv) * 0.05)
        goal_side = self.absolute(team.side, side_u, side_v)
        for body in candidates[:pressers]:
            if math.hypot(body.x - carrier.x, body.y - carrier.y) < self.ps["press_radius"]:
                body.tx, body.ty = goal_side

    def _base_speed(self, body: Body) -> float:
        m = self.pm
        return (
            m["speed_min"]
            + (m["speed_max"] - m["speed_min"])
            * ((body.attr("pace") + body.attr("acceleration")) / 2 - 1)
            / 19
        )

    def _speed(self, body: Body) -> float:
        return body.base_speed * (1 - self.pe["tired_speed"] * (1 - body.energy))

    def _move(self, dt: float) -> None:
        e = self.pe
        jog = self.pm["jog_share"]
        tired = e["tired_speed"]
        owner = self.ball.owner
        for team in self.teams.values():
            for body in team.bodies:
                if not body.on or body is owner:
                    continue
                dx, dy = body.tx - body.x, body.ty - body.y
                d = math.hypot(dx, dy)
                top = body.base_speed * (1 - tired * (1 - body.energy))
                speed = top if d > 4 else top * jog
                step = d if d < speed * dt else speed * dt
                if d > 1e-6:
                    body.x += dx / d * step
                    body.y += dy / d * step
                self._tire(body, step, top, dt, e)

    @staticmethod
    def _tire(body: Body, step: float, top: float, dt: float, e: Mapping[str, float]) -> None:
        body.distance += step
        effort = (step / dt) / top if top > 1e-6 else 0.0
        if effort > 0.8:
            body.sprint += step
        energy = body.energy - e["drain"] * dt * effort * effort / body.stamina
        if effort < 0.4:
            energy += e["recover"] * dt
        body.energy = 0.0 if energy < 0 else (1.0 if energy > 1 else energy)

    # ---- the ball --------------------------------------------------------------------------------

    def _restart(self, body: Body, kind: str) -> None:
        """A dead-ball restart taken by `body` after a realistic delay (throw-in, goal kick,
        corner, free kick, kick-off after a goal): the clock runs, the taker waits."""
        self._give(body)
        self.dead_until = self.t + self.pr[kind]
        self._next_decision = self.dead_until

    def _stoppage(self, kind: str) -> None:
        """Extra dead time for an event that stops play (a card, a substitution)."""
        self.dead_until = max(self.dead_until, self.t + self.pr[kind])
        self._next_decision = max(self._next_decision, self.dead_until)

    def _give(self, body: Body) -> None:
        self.ball.owner = body
        self.ball.flight = None
        self.ball.x, self.ball.y = body.x, body.y
        self._last_toucher = body

    def _nearest(
        self, team: Team, x: float, y: float, outfield: bool = False, exclude: Body | None = None
    ) -> Body | None:
        best = None
        best_d = 1e9
        for body in team.on_pitch():
            if body is exclude or (outfield and body.group is Group.GOALKEEPER):
                continue
            d = math.hypot(body.x - x, body.y - y)
            if d < best_d or (d == best_d and best is not None and body.pid < best.pid):
                best, best_d = body, d
        return best

    def _ball(self, dt: float) -> None:
        ball = self.ball
        if ball.owner is not None:
            carrier = ball.owner
            # the carrier runs with the ball into the space ahead; a defender in front of him
            # blocks the way (he shields and must pass or take him on: a dribble duel)
            u, v = self.rel(carrier.side, carrier.x, carrier.y)
            ahead = min(u + 6, self.pd["carry_limit_m"])
            pull = 0.15 if u < 75 else 0.45  # in the final third he cuts towards goal
            tu, tv = pitch.clamp_point(ahead, v + (pitch.CENTRE_V - v) * pull)
            tx, ty = self.absolute(carrier.side, tu, tv)
            dx, dy = tx - carrier.x, ty - carrier.y
            d = math.hypot(dx, dy)
            top = self._speed(carrier) * 0.8
            if self._blocked(carrier):
                top *= self.pdu["shield_speed"]
            step = min(d, top * dt)
            if d > 1e-6:
                carrier.x += dx / d * step
                carrier.y += dy / d * step
            self._tire(carrier, step, top, dt, self.pe)
            ball.x, ball.y = carrier.x, carrier.y
            return
        if ball.flight is None:
            return
        tx, ty, arrival = ball.flight
        remaining = arrival - self.t
        if remaining <= dt:
            ball.x, ball.y = tx, ty
            self._land()
        else:
            ball.x += (tx - ball.x) * dt / remaining
            ball.y += (ty - ball.y) * dt / remaining

    def _launch(
        self, tx: float, ty: float, speed: float, landing: str, receiver: Body | None = None
    ) -> None:
        ball = self.ball
        d = math.hypot(tx - ball.x, ty - ball.y)
        ball.flight = (tx, ty, self.t + max(0.25, d / speed))
        ball.landing = landing
        ball.receiver = receiver
        ball.owner = None

    def _land(self) -> None:
        ball = self.ball
        landing = ball.landing
        ball.flight = None
        if (landing == "receive" and ball.receiver is not None and ball.receiver.on) or (
            landing == "intercept" and ball.receiver is not None and ball.receiver.on
        ):
            ball.receiver.x, ball.receiver.y = ball.x, ball.y
            self._give(ball.receiver)
            self._next_decision = self.t + self.p["decide"]["control_delay_s"]
        elif landing == "shot":
            self._resolve_shot()
        else:
            self._out_of_play()

    # ---- decisions -------------------------------------------------------------------------------

    def _decide(self, carrier: Body) -> None:
        d = self.p["decide"]
        team = self.teams[carrier.side]
        opp = self.teams[other(carrier.side)]
        u, v = self.rel(carrier.side, carrier.x, carrier.y)
        intent = self._intent(team)
        risk = _mentality_index(team.tactic.mentality) - 3
        if intent == "chase":
            risk += 2
        elif intent == "protect":
            risk -= 2
        options: list[tuple[float, str, object]] = []
        pressure = self._pressure(carrier, opp)
        # shoot
        if pitch.LENGTH - u <= d["shot_range_m"]:
            blockers = self._blockers(carrier, opp)
            value = pitch.xg(u, v, self.px, blockers=blockers)
            far = pitch.LENGTH - u > 20
            bias = d["shoot_bias"]
            if far:
                bias *= {"reduced": 0.7, "balanced": 1.0, "encouraged": 1.3}.get(
                    team.tactic.setting("shots_from_distance"), 1.0
                )
            long_shots = carrier.attr("long_shots") if far else 10.0
            if value >= d["min_shot_xg"] * (1.4 - long_shots / 25):
                options.append((value * bias * (1 + 0.05 * risk), "shoot", blockers))
        # pass to each teammate
        here = self._threat(u, v)
        directness = {
            "much_shorter": -2,
            "shorter": -1,
            "balanced": 0,
            "more_direct": 1,
            "much_more_direct": 2,
        }.get(team.tactic.setting("passing_directness"), 0)
        line = self.offside_line(carrier.side)
        for mate in team.on_pitch():
            if mate is carrier:
                continue
            mu, mv = self.rel(carrier.side, mate.x, mate.y)
            if mu > line + 0.3:
                continue  # offside
            dist = math.hypot(mu - u, mv - v)
            if dist < 4 or dist > d["pass_max_m"]:
                continue
            crowd = self._crowd(mate, opp)
            p_ok = self._pass_success(carrier, mate, dist, pressure, opp, crowd)
            gain = self._threat(mu, mv) / (1 + d["crowd_discount"] * crowd)
            value = p_ok * gain - (1 - p_ok) * d["loss_cost"] * self._threat(
                pitch.LENGTH - mu, pitch.WIDTH - mv
            )
            value *= d["pass_bias"] * (1 + 0.04 * directness * (mu - u) / 10)
            options.append((value, "pass", (mate, p_ok)))
        # carry into space, or take on the defender in front
        forward = self._threat(min(pitch.LENGTH - 1, u + 8), v)
        blocker = self._blocked(carrier)
        if blocker is None:
            options.append((0.95 * forward * d["carry_bias"], "dribble", 0.95))
        else:
            beat = self._beat_chance(carrier, opp, blocker)
            options.append(
                (beat * forward * d["dribble_bias"] * (1 + 0.04 * risk), "dribble", beat)
            )
        # cross from wide in the final third
        if u > 75 and abs(v - pitch.CENTRE_V) > 18:
            value = 0.35 * self.p["set_pieces"]["corner_header_xg"] * 2 * d["cross_bias"]
            options.append((value, "cross", None))
        # clear under pressure near the own goal
        if u < 25 and pressure > 0.5:
            options.append((0.004 * d["clear_bias"], "clear", None))
        choice = self._choose(carrier, options, here)
        kind, payload = choice[1], choice[2]
        if kind == "shoot":
            assert isinstance(payload, int)
            self._shoot(carrier, u, v, payload)
        elif kind == "pass":
            assert isinstance(payload, tuple)
            self._pass(carrier, payload[0], payload[1], opp)
        elif kind == "cross":
            self._cross(carrier, team, opp)
        elif kind == "clear":
            self._clear(carrier)
        else:
            self._dribble(carrier, opp)

    def _dribble(self, carrier: Body, opp: Team) -> None:
        """Take on the defender in front (if any): past him, or the ball is lost."""
        blocker = self._blocked(carrier)
        if blocker is None:
            self._next_decision = self.t + self.pd["decision_every_s"]
            return
        if self.rng.random() < self._beat_chance(carrier, opp, blocker):
            u, v = self.rel(carrier.side, carrier.x, carrier.y)
            past_u, past_v = pitch.clamp_point(
                u + self.pdu["beat_advance"], v + self.rng.choice((-1.5, 1.5))
            )
            carrier.x, carrier.y = self.absolute(carrier.side, past_u, past_v)
            bu, bv = self.rel(carrier.side, blocker.x, blocker.y)
            blocker.x, blocker.y = self.absolute(carrier.side, *pitch.clamp_point(bu - 1.5, bv))
            self.ball.x, self.ball.y = carrier.x, carrier.y
            self._next_decision = self.t + self.pd["decision_every_s"] * 0.6
        else:
            self._give(blocker)
            self._next_decision = self.t + self.pd["control_delay_s"]

    def _choose(
        self, carrier: Body, options: Sequence[tuple[float, str, object]], here: float
    ) -> tuple[float, str, object]:
        d = self.p["decide"]
        skill = (carrier.attr("decisions") + carrier.attr("composure")) / 40
        temperature = d["temperature"] * (1.3 - skill) * (1 + (1 - carrier.energy) * 0.5)
        best = max(v for v, _, _ in options)
        scale = max(1e-4, abs(best) * temperature)
        weights = [math.exp((v - best) / scale) for v, _, _ in options]
        total = sum(weights)
        r = self.rng.random() * total
        for weight, option in zip(weights, options, strict=True):
            r -= weight
            if r <= 0:
                return option
        return options[-1]

    def _threat(self, u: float, v: float) -> float:
        """The value of having the ball at (u, v): mostly the chance of a good shot from there."""
        return 0.004 + 0.01 * (u / pitch.LENGTH) ** 2 + 0.5 * pitch.xg(u, v, self.p["xg"])

    def offside_line(self, side: str) -> float:
        """In `side`'s view: how far forward an attacker may be when the ball is played (Law
        11): level with the second-last opponent, or the halfway line, or the ball."""
        opp = self.teams[other(side)]
        depths = sorted((self.rel(side, b.x, b.y)[0] for b in opp.bodies if b.on), reverse=True)
        second_last = depths[1] if len(depths) > 1 else pitch.LENGTH
        ball_u = self.rel(side, self.ball.x, self.ball.y)[0]
        return max(pitch.LENGTH / 2, second_last, ball_u)

    def _blocked(self, carrier: Body) -> Body | None:
        """The nearest opponent standing in front of the carrier (towards the goal he attacks),
        if any: within `block_depth` ahead and `block_width` to either side."""
        opp = self.teams[other(carrier.side)]
        u, v = self.rel(carrier.side, carrier.x, carrier.y)
        depth = self.pdu["block_depth"]
        width = self.pdu["block_width"]
        best = None
        best_d = 99.0
        for body in opp.bodies:
            if not body.on:
                continue
            bu, bv = self.rel(carrier.side, body.x, body.y)
            ahead = bu - u
            if -0.5 <= ahead <= depth and abs(bv - v) <= width and ahead < best_d:
                best, best_d = body, ahead
        return best

    def _pressure(self, carrier: Body, opp: Team) -> float:
        closest = min(
            (math.hypot(b.x - carrier.x, b.y - carrier.y) for b in opp.on_pitch()), default=99.0
        )
        return max(0.0, 1 - closest / 6)

    def _blockers(self, carrier: Body, opp: Team) -> int:
        gx = pitch.LENGTH if self.attacks_positive(carrier.side) else 0.0
        goal = (gx, pitch.CENTRE_V)
        return sum(
            1
            for b in opp.on_pitch()
            if b.group is not Group.GOALKEEPER
            and pitch.point_segment_distance((b.x, b.y), (carrier.x, carrier.y), goal)
            < self.px["block_lane"]
        )

    def _crowd(self, mate: Body, opp: Team) -> int:
        """Defenders within `crowd_radius` of a teammate (he would receive under pressure)."""
        radius = self.pd["crowd_radius"]
        return sum(
            1
            for b in opp.bodies
            if b.on
            and abs(b.x - mate.x) < radius
            and abs(b.y - mate.y) < radius
            and math.hypot(b.x - mate.x, b.y - mate.y) < radius
        )

    def _pass_success(
        self, carrier: Body, mate: Body, dist: float, pressure: float, opp: Team, crowd: int = 0
    ) -> float:
        d = self.p["decide"]
        skill = (
            2 * carrier.attr("passing") + carrier.attr("vision") + carrier.attr("technique")
        ) / 80
        base = 0.97 - dist * 0.006 * (1.4 - skill) - pressure * d["pressure_pass"]
        lane = 0
        for b in opp.on_pitch():
            if (
                pitch.point_segment_distance((b.x, b.y), (carrier.x, carrier.y), (mate.x, mate.y))
                < d["intercept_radius"]
            ):
                lane += 1
        base *= d["lane_pass"] ** lane
        base *= self.pd["crowd_pass"] ** crowd
        base *= 1 + self.edge[carrier.side]
        return max(0.05, min(0.98, base))

    def _beat_chance(self, carrier: Body, opp: Team, nearest: Body | None = None) -> float:
        if nearest is None:
            nearest = self._blocked(carrier)
        if nearest is None:
            return 0.95
        attack = (carrier.attr("dribbling") + carrier.attr("agility") + carrier.attr("pace")) / 3
        defend = (nearest.attr("tackling") + nearest.attr("positioning") + nearest.attr("pace")) / 3
        chance = 0.5 + self.pdu["dribble_skill"] * (attack - defend) + self.edge[carrier.side]
        return max(0.15, min(0.85, chance))

    # ---- actions ---------------------------------------------------------------------------------

    def _pass(self, carrier: Body, mate: Body, p_ok: float, opp: Team) -> None:
        speed = self.p["movement"]["ball_speed_pass"]
        dist = math.hypot(mate.x - carrier.x, mate.y - carrier.y)
        if dist > 25:
            speed = self.p["movement"]["ball_speed_long"]
        self.passes += 1
        if self.rng.random() < p_ok:
            self.passes_completed += 1
            self.ball.passer = carrier
            self._launch(mate.x, mate.y, speed, "receive", mate)
            return
        # misplaced: an opponent near the line wins it, or it runs out of play
        cut = self._nearest(opp, (carrier.x + mate.x) / 2, (carrier.y + mate.y) / 2)
        if cut is not None and self.rng.random() < 0.8:
            self.ball.passer = None
            self._launch(cut.x, cut.y, speed, "intercept", cut)
        else:
            tx, ty = mate.x + self.rng.uniform(-8, 8), mate.y + self.rng.uniform(-8, 8)
            self.ball.passer = None
            self._launch(
                tx,
                ty,
                speed,
                "out" if not _inside(tx, ty) else "intercept",
                self._nearest(opp, tx, ty),
            )
            if _inside(tx, ty) and self.ball.receiver is None:
                self.ball.landing = "out"

    def _shoot(
        self, carrier: Body, u: float, v: float, blockers: int, header: bool = False
    ) -> None:
        team = self.teams[carrier.side]
        value = pitch.xg(u, v, self.p["xg"], header=header, blockers=blockers)
        team.shots += 1
        team.xg += value
        gx = pitch.LENGTH if self.attacks_positive(carrier.side) else 0.0
        self.ball.shot_xg = value
        self.ball.shooter = carrier
        self._launch(
            gx,
            pitch.CENTRE_V + self.rng.uniform(-3, 3),
            self.p["movement"]["ball_speed_shot"],
            "shot",
        )

    def _resolve_shot(self) -> None:
        shooter = self.ball.shooter
        if shooter is None:
            self._out_of_play()
            return
        team = self.teams[shooter.side]
        opp = self.teams[other(shooter.side)]
        value = self.ball.shot_xg
        finishing = (shooter.attr("finishing") + shooter.attr("composure")) / 2
        on_target = min(0.92, 0.28 + 0.9 * value + 0.012 * (finishing - 10))
        if self.rng.random() >= on_target:
            if self.rng.random() < 0.25:  # blocked or deflected wide
                self._corner(shooter.side)
            else:
                self._goal_kick(opp.side)
            return
        team.on_target += 1
        keeper = opp.keeper()
        k = self.p["keeper"]
        keeper_skill = (
            10.0
            if keeper is None
            else (keeper.attr("reflexes") + keeper.attr("handling") + keeper.attr("one_on_ones"))
            / 3
        )
        score = min(
            0.97,
            value
            / on_target
            * (1 + 0.02 * (finishing - 10))
            * (1 - k["save_skill"] * (keeper_skill - 10))
            * (1 + self.edge[shooter.side]),
        )
        if self.rng.random() < score:
            self._goal(shooter, value)
        elif keeper is not None and self.rng.random() < 0.75:  # most saves are held
            self._restart(keeper, "keeper_hold")
        else:
            self._corner(shooter.side)

    def _goal(self, scorer: Body, value: float) -> None:
        team = self.teams[scorer.side]
        team.goals += 1
        assister = (
            self.ball.passer
            if self.ball.passer is not None
            and self.ball.passer.side == scorer.side
            and self.ball.passer is not scorer
            else None
        )
        if self.rng.random() < self.q.rates.own_goal_share:
            opp = self.teams[other(scorer.side)]
            culprit = self._nearest(opp, self.ball.x, self.ball.y)
            if culprit is not None:
                self._event(scorer.side, "own_goal", culprit.pid)
                self._kickoff(other(scorer.side))
                self._stoppage("goal")
                return
        self._event(
            scorer.side,
            "goal",
            scorer.pid,
            assister.pid if assister is not None else None,
            round(value, 3),
        )
        self._kickoff(other(scorer.side))
        self._stoppage("goal")

    def _cross(self, carrier: Body, team: Team, opp: Team) -> None:
        targets = [
            b for b in team.on_pitch() if b is not carrier and b.group is not Group.GOALKEEPER
        ]
        box = [b for b in targets if pitch.in_box(*self.rel(team.side, b.x, b.y))]
        if not box:
            self._next_decision = self.t + self.p["decide"]["decision_every_s"]
            return
        target = max(box, key=lambda b: (b.attr("heading") + b.attr("jumping_reach"), b.pid))
        keeper = opp.keeper()
        claim = 0.15 if keeper is None else 0.08 + 0.01 * keeper.attr("command_of_area")
        quality = (carrier.attr("crossing") + target.attr("heading")) / 40
        if self.rng.random() < claim:
            if keeper is not None:
                self._give(keeper)
                self._next_decision = self.t + 1.5
            return
        if self.rng.random() < 0.25 + 0.25 * quality:
            tu, tv = self.rel(team.side, target.x, target.y)
            self.ball.passer = carrier
            self._give(target)
            self._shoot(target, tu, tv, self._blockers(target, opp), header=True)
        else:
            defender = self._nearest(opp, target.x, target.y)
            if defender is not None and self.rng.random() < 0.6:
                self._give(defender)
                self._next_decision = self.t + 0.5
            else:
                self._corner(team.side)

    def _clear(self, carrier: Body) -> None:
        u, v = self.rel(carrier.side, carrier.x, carrier.y)
        tu, tv = pitch.clamp_point(u + self.rng.uniform(30, 50), v + self.rng.uniform(-20, 20))
        tx, ty = self.absolute(carrier.side, tu, tv)
        opp = self.teams[other(carrier.side)]
        team = self.teams[carrier.side]
        landing = min(
            (self._nearest(opp, tx, ty), self._nearest(team, tx, ty, exclude=carrier)),
            key=lambda b: (
                99.0 if b is None else math.hypot(b.x - tx, b.y - ty) + (self.rng.random() * 6)
            ),
        )
        self.ball.passer = None
        self._launch(tx, ty, self.p["movement"]["ball_speed_long"], "intercept", landing)

    # ---- duels, fouls and cards ------------------------------------------------------------------

    def _duels(self, dt: float) -> None:
        carrier = self.ball.owner
        if carrier is None:
            return
        self._duel_clock += dt
        if self._duel_clock < self.p["duel"]["duel_every_s"]:
            return
        self._duel_clock = 0.0
        opp = self.teams[other(carrier.side)]
        du = self.p["duel"]
        for body in opp.on_pitch():
            if body.group is Group.GOALKEEPER:
                continue
            if math.hypot(body.x - carrier.x, body.y - carrier.y) > du["duel_radius"]:
                continue
            tackle = (body.attr("tackling") + body.attr("positioning") + body.attr("strength")) / 3
            keep = (
                carrier.attr("dribbling") + carrier.attr("balance") + carrier.attr("strength")
            ) / 3
            win = du["tackle_base"] + du["dribble_skill"] * (tackle - keep) + self.edge[body.side]
            win *= 0.8 + 0.4 * body.energy
            win *= {"ease_off": 0.85, "standard": 1.0, "aggressive": 1.12}.get(
                opp.tactic.setting("tackling"), 1.0
            )
            foul = (
                du["foul_base"]
                * (discipline_score(body.player) / 10) ** self.q.fouls.fouler_exponent
            )
            foul *= {"ease_off": 0.85, "standard": 1.0, "aggressive": 1.15}.get(
                opp.tactic.setting("tackling"), 1.0
            )
            if body.yellow:
                foul *= 1 - (1 - self.q.caution.foul) * caution_strength(body.player, self.q)
            r = self.rng.random()
            if r < foul:
                self._foul(body, carrier)
                return
            if r < foul + win * 0.5:
                self._give(body)
                self._next_decision = self.t + self.p["decide"]["control_delay_s"]
                return

    def _foul(self, fouler: Body, victim: Body) -> None:
        team = self.teams[fouler.side]
        team.fouls += 1
        q = self.q
        proneness = (discipline_score(fouler.player) / 10) ** q.fouls.card_exponent
        minute = self.minute()
        if self.rng.random() < q.rates.direct_red_per_foul * proneness:
            self._send_off(fouler, "red")
        else:
            ramp = q.fouls.card_minute_start + q.fouls.card_minute_span * min(minute.base, 90) / 90
            card = q.rates.yellow_per_foul * proneness * ramp
            if fouler.yellow:
                card *= 1 - (1 - q.caution.card) * caution_strength(fouler.player, q)
            if self.rng.random() < card:
                if fouler.yellow:
                    self._send_off(fouler, "second_yellow")
                else:
                    fouler.yellow = True
                    self._event(fouler.side, "yellow", fouler.pid)
                self._stoppage("card")
        u, v = self.rel(victim.side, victim.x, victim.y)
        if pitch.in_box(u, v):
            self._stoppage("penalty")
            self._penalty(victim.side)
        else:
            self._restart(victim, "free_kick")

    def _send_off(self, body: Body, kind: str) -> None:
        body.on = False
        self._event(body.side, kind, body.pid)
        team = self.teams[body.side]
        if body.group is Group.GOALKEEPER:
            replacement = next(
                (b for b in team.on_pitch() if b.group is not Group.GOALKEEPER), None
            )
            if replacement is not None:
                replacement.position = Position.GK

    def _penalty(self, side: str) -> None:
        team = self.teams[side]
        opp = self.teams[other(side)]
        outfield = [b.player for b in team.on_pitch() if b.group is not Group.GOALKEEPER]
        if not outfield:
            return
        keeper_body = team.keeper()
        taker = penalty_taker(outfield, keeper_body.player if keeper_body else None, self.q)
        opp_keeper = opp.keeper()
        pen = self.q.penalties
        probability = (
            pen.conversion
            * kick_factor(self.q, taker, opp_keeper.player if opp_keeper else None)
            / self.q.shootout.base
        )
        team.shots += 1
        team.xg += pen.xg
        if self.rng.random() < min(pen.conversion_max, probability):
            team.on_target += 1
            team.goals += 1
            self._event(side, "penalty_goal", taker.id, None, pen.xg)
            self._kickoff(other(side))
            self._stoppage("goal")
        else:
            if self.rng.random() < pen.miss_saved:
                team.on_target += 1
            self._event(side, "penalty_miss", taker.id, None, pen.xg)
            self._goal_kick(other(side))

    # ---- restarts --------------------------------------------------------------------------------

    def _out_of_play(self) -> None:
        last = self._last_toucher
        side = other(last.side) if last is not None else HOME
        team = self.teams[side]
        taker = self._nearest(team, self.ball.x, self.ball.y, outfield=True)
        if taker is not None:
            x, y = pitch.clamp_point(self.ball.x, self.ball.y)
            taker.x, taker.y = x, y
            self._restart(taker, "throw_in")

    def _goal_kick(self, side: str) -> None:
        team = self.teams[side]
        keeper = team.keeper() or self._nearest(team, 0, 0)
        if keeper is None:
            return
        keeper.x, keeper.y = self.absolute(side, 6.0, pitch.CENTRE_V)
        self._restart(keeper, "goal_kick")

    def _corner(self, side: str) -> None:
        team = self.teams[side]
        opp = self.teams[other(side)]
        team.corners += 1
        taker = max(
            (b for b in team.on_pitch() if b.group is not Group.GOALKEEPER),
            key=lambda b: (b.attr("corners"), b.pid),
            default=None,
        )
        if taker is None:
            return
        y = 0.5 if self.rng.random() < 0.5 else pitch.WIDTH - 0.5
        taker.x, taker.y = self.absolute(side, pitch.LENGTH - 0.5, y)
        attackers = sorted(
            (b for b in team.on_pitch() if b is not taker and b.group is not Group.GOALKEEPER),
            key=lambda b: (-(b.attr("heading") + b.attr("jumping_reach")), b.pid),
        )[:4]
        for i, body in enumerate(attackers):
            body.x, body.y = self.absolute(
                side, pitch.LENGTH - 6 - i * 2, pitch.CENTRE_V - 6 + i * 4
            )
        self._give(taker)
        self._stoppage("corner")
        self._cross(taker, team, opp)

    # ---- substitutions and decisions -------------------------------------------------------------

    def _assistant_subs(self, base: int) -> None:
        for side in (HOME, AWAY):
            count = self._windows_plan[side].pop(base, 0)
            if count and not self._user_side_locked(side):
                self._auto_subs(self.teams[side], count)

    def _halftime_subs(self) -> None:
        for side in (HOME, AWAY):
            if not self._user_side_locked(side) and self.rng.random() < self.q.subs.halftime_chance:
                self._auto_subs(self.teams[side], 1, halftime=True)

    def _user_side_locked(self, side: str) -> bool:
        """A side whose manager has made a decision manages his own substitutions."""
        return any(d.side == side for d in self.decisions)

    def _auto_subs(self, team: Team, count: int, halftime: bool = False) -> None:
        q = self.q
        if not halftime and team.windows >= 3:
            return
        made = 0
        for _ in range(count):
            if team.subs >= q.subs.max or not team.bench:
                break
            candidates = [
                b
                for b in team.on_pitch()
                if b.group is not Group.GOALKEEPER and b.pid not in team.came_on
            ]
            if not candidates:
                break
            out = min(candidates, key=lambda b: (b.energy - (0.15 if b.yellow else 0), b.pid))
            bench = [
                pid
                for pid in team.bench
                if POSITION_GROUP[_best_position(self.players[pid])] is not Group.GOALKEEPER
            ]
            if not bench:
                break
            incoming = max(bench, key=lambda pid: (self.players[pid].positions[out.position], pid))
            self._swap(team, out, incoming)
            made += 1
        if made and not halftime:
            team.windows += 1

    def _swap(self, team: Team, out: Body, incoming: str) -> None:
        out.on = False
        body = Body(
            incoming,
            team.side,
            out.slot,
            self.players[incoming],
            out.position,
            out.x,
            out.y,
            out.tx,
            out.ty,
        )
        body.base_speed = self._base_speed(body)
        team.bodies.append(body)
        team.bench.remove(incoming)
        team.came_on.add(incoming)
        team.played.add(incoming)
        team.subs += 1
        if self.ball.owner is out:
            self._give(body)
        self._event(team.side, "sub", out.pid, incoming)
        self._stoppage("substitution")
        if self.recording:
            self.sub_samples.append((len(self.samples), self._slot_index(body), incoming))

    def _apply(self, decision: Decision) -> None:
        self.decisions.append(decision)
        team = self.teams[decision.side]
        if decision.kind == "substitution" and decision.off and decision.on:
            out = next(b for b in team.on_pitch() if b.pid == decision.off)
            self._swap(team, out, decision.on)
            # one window per stoppage; changes at half-time use none (IFAB)
            if not self.at_half_time() and self._last_window[decision.side] != decision.at:
                team.windows += 1
                self._last_window[decision.side] = decision.at
        elif decision.kind == "tactic" and decision.tactic is not None:
            team.tactic = decision.tactic

    # ---- output ----------------------------------------------------------------------------------

    def _event(
        self,
        side: str,
        kind: str,
        pid: str,
        other_pid: str | None = None,
        xg_value: float | None = None,
    ) -> None:
        self.events.append(MatchEvent(self.minute(), side, kind, pid, other_pid, xg_value))
        if self.recording:
            self.event_samples.append((len(self.samples), len(self.events) - 1))

    def _slot_index(self, body: Body) -> int:
        return body.slot + (0 if body.side == HOME else 11)

    def _sample(self) -> None:
        values = [to_cm(self.ball.x), to_cm(self.ball.y), 0]
        positions = [(OFF_PITCH, OFF_PITCH)] * SLOTS
        for team in self.teams.values():
            for body in team.on_pitch():
                index = self._slot_index(body)
                if 0 <= index < SLOTS:
                    positions[index] = (to_cm(body.x), to_cm(body.y))
        for x, y in positions:
            values.extend((x, y))
        self.samples.append(tuple(values))

    def record(self) -> PositionalRecord:
        players: list[tuple[str, str]] = []
        for side in (HOME, AWAY):
            starters = sorted(self.teams[side].sheet.starters)
            players.extend((pid, side) for _, pid in starters)
        return PositionalRecord(
            1 / (self.p["time"]["step_s"] * self.p["time"]["record_every_steps"]),
            tuple(players),
            tuple(self.samples),
            tuple(self.event_samples),
            tuple(self.sub_samples),
        )

    def report(self) -> MatchReport:
        home, away = self.teams[HOME], self.teams[AWAY]
        owned = home.owned_s + away.owned_s
        home_poss = round(100 * home.owned_s / owned) if owned else 50

        def stats(team: Team, possession: int) -> SideStats:
            yellows, reds = card_counts(self.events, team.side)
            return SideStats(
                team.goals,
                team.shots,
                team.on_target,
                round(team.xg, 2),
                possession,
                team.corners,
                team.fouls,
                yellows,
                reds,
            )

        def lineup(team: Team) -> SideLineup:
            sheet = team.sheet
            return SideLineup(
                sheet.club_id,
                sheet.formation.name,
                tuple((sheet.slot_position(i), pid) for i, pid in sheet.starters),
                sheet.bench,
                sheet.flags,
            )

        def keeper(team: Team) -> str | None:
            body = team.keeper()
            return body.pid if body is not None else None

        def summary(team: Team) -> TacticSummary:
            t = team.tactic
            return TacticSummary(
                t.ip_formation, t.oop_formation, team.start_mentality, t.style, tactic_digest(t)
            )

        return MatchReport(
            home=stats(home, home_poss),
            away=stats(away, 100 - home_poss),
            events=tuple(self.events),
            home_lineup=lineup(home),
            away_lineup=lineup(away),
            home_finishers=tuple(b.pid for b in home.on_pitch()),
            away_finishers=tuple(b.pid for b in away.on_pitch()),
            stoppage=self.stoppage,
            model_version=f"positional {self.p.model_version}",
            home_keeper=keeper(home),
            away_keeper=keeper(away),
            home_tactic=summary(home),
            away_tactic=summary(away),
        )

    def result(self) -> Result:
        report = self.report()
        return Result(
            report.home.goals,
            report.away.goals,
            SOURCE,
            home_red=report.home.reds,
            away_red=report.away.reds,
            home_yellow=report.home.yellows,
            away_yellow=report.away.yellows,
            report=report,
        )


def _inside(x: float, y: float) -> bool:
    return 0 < x < pitch.LENGTH and 0 < y < pitch.WIDTH


def _mentality_index(mentality: str) -> int:
    order = (
        "very_defensive",
        "defensive",
        "cautious",
        "balanced",
        "positive",
        "attacking",
        "very_attacking",
    )
    return order.index(mentality) if mentality in order else 3


def _best_position(player: Player) -> Position:
    return max(player.positions.items(), key=lambda item: (item[1], item[0].value))[0]


def _formation(name: str, sheet: TeamSheet):  # type: ignore[no-untyped-def]
    from manager_core.domain.formation import load_catalogue

    catalogue = load_catalogue()
    return catalogue.get(name, sheet.formation)


def simulate_positional(
    home: TeamSheet,
    away: TeamSheet,
    players: Mapping[str, Player],
    params: PositionalParams,
    qparams: ModelParams,
    rng: random.Random,
    neutral: bool = False,
    home_tactic: Tactic | None = None,
    away_tactic: Tactic | None = None,
    record: bool = False,
) -> tuple[Result, LiveMatch]:
    """Play a whole match with no user decisions (background use, tests, calibration)."""
    match = LiveMatch(
        home, away, players, params, qparams, rng, neutral, home_tactic, away_tactic, record
    )
    match.play()
    return match.result(), match
