"""The quick-sim match engine: a minute-by-minute event model (research R1-R8).

Each minute, each side may shoot (with an xG), win a penalty or a corner, and commit a foul that
can lead to a card. Rates come from the team ratings of the players on the pitch, home advantage,
a time trend and the game state. All randomness comes from the match's own RNG, and players are
always iterated in a fixed order, so a match is a pure function of its inputs and seed.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from manager_core.competition.results import Result
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.quicksim.params import LineWeights, ModelParams
from manager_core.quicksim.ratings import (
    POSITION_GROUP,
    Group,
    TeamRatings,
    combine,
    contribution,
    player_composites,
    slot_contributions,
)
from manager_core.quicksim.report import (
    AWAY,
    HALF_TIME,
    HOME,
    MatchEvent,
    MatchReport,
    Minute,
    SideLineup,
    SideStats,
    card_counts,
    other,
)
from manager_core.quicksim.squad import TeamSheet

SOURCE = "quick_sim"


def _attr(p: Player, name: str) -> int:
    return p.attributes.get(name)


@dataclass
class _Side:
    """Mutable state of one side during a match."""

    name: str
    sheet: TeamSheet
    players: Mapping[str, Player]
    on: dict[int, str]  # slot index -> player id
    bench: list[str]
    ratings: TeamRatings = field(init=False)
    composites: dict[str, dict[str, float]] = field(default_factory=dict)
    _contrib: dict[tuple[str, int], tuple[float, ...]] = field(default_factory=dict)
    goals: int = 0
    shots: int = 0
    on_target: int = 0
    xg: float = 0.0
    corners: int = 0
    fouls: int = 0
    yellows: dict[str, int] = field(default_factory=dict)
    sent_off: int = 0
    subs: int = 0
    windows: int = 0
    played: set[str] = field(default_factory=set)
    came_on: set[str] = field(default_factory=set)  # substitutes are not withdrawn again

    def player(self, pid: str) -> Player:
        return self.players[pid]

    def on_pitch(self) -> list[tuple[int, str]]:
        return sorted(self.on.items())

    def refresh(self, params: ModelParams) -> None:
        slots = self.sheet.slot_positions
        cost = 0.0
        if params.caution.enabled:
            cost = sum(params.caution.cost * contribution(self.player(pid), slots[i], "defence",
                                                          self.composites[pid])
                       for i, pid in self.on.items() if self.yellows.get(pid))
        self.ratings = combine([(slots[i], self._slot_contrib(pid, i))
                                for i, pid in sorted(self.on.items(), key=lambda x: x[1])],
                               slots, defence_penalty=cost)

    def _slot_contrib(self, pid: str, slot: int) -> tuple[float, ...]:
        key = (pid, slot)
        if key not in self._contrib:
            self._contrib[key] = slot_contributions(
                self.player(pid), self.sheet.slot_position(slot), self.composites[pid])
        return self._contrib[key]

    def discipline(self, pid: str) -> float:
        return self.composites[pid]["discipline"]

    def group_of(self, slot_index: int) -> Group:
        return POSITION_GROUP[self.sheet.slot_position(slot_index)]


def _weighted(rng: random.Random, items: Sequence[tuple[str, float]]) -> str | None:
    total = sum(w for _, w in items)
    if total <= 0:
        return None
    pick = rng.random() * total
    for item, weight in items:
        pick -= weight
        if pick < 0:
            return item
    return items[-1][0]


class _Match:
    def __init__(self, home: TeamSheet, away: TeamSheet, players: Mapping[str, Player],
                 params: ModelParams, rng: random.Random, neutral: bool) -> None:
        self.params = params
        self.rng = rng
        self.neutral = neutral
        self.events: list[MatchEvent] = []
        self.sides = {
            HOME: _Side(HOME, home, players, dict(home.starters), list(home.bench)),
            AWAY: _Side(AWAY, away, players, dict(away.starters), list(away.bench)),
        }
        for s in self.sides.values():
            s.played = set(s.on.values())
            s.composites = {pid: player_composites(players[pid])
                            for pid in sorted({*s.on.values(), *s.bench})}
            s.refresh(params)

    # ---- helpers -------------------------------------------------------------------------

    def _event(self, minute: Minute, side: str, kind: str, player_id: str,
               other_id: str | None = None, xg: float | None = None) -> None:
        self.events.append(MatchEvent(minute, side, kind, player_id, other_id, xg))

    def _line_weight(self, group: Group) -> float:
        return line_weight(self.params.scorers.line_weights, group)

    # ---- the minute loop -------------------------------------------------------------------

    def play(self) -> tuple[int, int]:
        p = self.params
        stop1 = self.rng.randint(*p.stoppage.first)
        stop2 = self.rng.randint(*p.stoppage.second)
        windows = {s: self._plan_subs() for s in (HOME, AWAY)}
        minutes = ([Minute(m) for m in range(1, 46)] + [Minute(45, k) for k in range(1, stop1 + 1)]
                   + [Minute(m) for m in range(46, 91)]
                   + [Minute(90, k) for k in range(1, stop2 + 1)])
        for minute in minutes:
            if minute == Minute(HALF_TIME):
                for s in (HOME, AWAY):
                    if self.rng.random() < p.subs.halftime_chance:
                        self._substitute(s, minute, 1, halftime=True)
            for s in (HOME, AWAY):
                if minute in windows[s]:
                    self._substitute(s, minute, windows[s][minute])
            for s in (HOME, AWAY):
                self._minute(s, minute)
        return stop1, stop2

    def _plan_subs(self) -> dict[Minute, int]:
        p = self.params.subs
        plan: dict[Minute, int] = {}
        for lo, hi in p.windows:
            minute = Minute(self.rng.randint(lo, hi))
            count = self.rng.randint(*p.per_window)
            if self.rng.random() < p.window_chance:
                plan[minute] = plan.get(minute, 0) + count
        return plan

    def _state(self, side: str, base: int) -> tuple[float, float]:
        """(own shot-rate multiplier, multiplier on the quality of chances conceded)."""
        p = self.params.state
        me, opp = self.sides[side], self.sides[other(side)]
        diff = me.goals - opp.goals
        rate_mult, conceded_quality = 1.0, 1.0
        if diff < 0 and base >= 60:
            push = (min(base, 90) - 60) / 30  # a bigger deficit does not push harder
            rate_mult *= 1 + p.chase * push
            conceded_quality *= 1 + p.exposed * push
        if abs(diff) >= 2:
            rate_mult *= 1 - p.settled
        if diff == 0 and base >= 60:
            rate_mult *= 1 + p.level * (min(base, 90) - 60) / 30
        if diff == 1 and base >= 70:
            rate_mult *= 1 - p.protect
            conceded_quality *= 1 - p.protect / 2
        man_diff = len(me.on) - len(opp.on)
        if man_diff > 0:
            rate_mult *= 1 + p.man_up * man_diff
        if me.sent_off:
            rate_mult *= (1 - p.short_handed) ** me.sent_off
        return rate_mult, conceded_quality

    def _minute(self, side: str, minute: Minute) -> None:
        p = self.params
        me, opp = self.sides[side], self.sides[other(side)]
        if not me.on:
            return
        base = minute.base
        # tempo rises within each half (teams settle, then open up and tire); it restarts at
        # half-time, so the first 15 minutes of each half are the quietest
        in_half = min(base, 45) if base <= 45 else min(base, 90) - 45
        span = p.time.trend_end - p.time.trend_start
        trend = p.time.trend_start + span * (in_half - 1) / 44
        if base > 45:
            trend *= p.time.second_half
        own_mult, _ = self._state(side, base)
        _, opp_conceded_quality = self._state(other(side), base)
        home = 1.0
        if not self.neutral:
            home = p.home.shot if side == HOME else p.home.away_shot
        r, o = me.ratings, opp.ratings
        edge = p.strength.attack * (r.attack - o.defence) / 5
        control = p.strength.control * (r.control - o.control) / 5
        pressure = math.exp(edge + control) * home * trend * own_mult
        rng = self.rng

        if rng.random() < p.rates.shot * pressure:
            median = p.strength.xg_median * math.exp(
                p.strength.xg_attack * (r.attack - o.defence) / 5)
            xg = median * opp_conceded_quality * math.exp(p.strength.xg_sigma * rng.gauss(0, 1))
            self._shot(side, minute, min(p.shots.xg_max, max(p.shots.xg_min, xg)))
            if rng.random() < p.rates.corner_per_shot:
                me.corners += 1
        if rng.random() < p.rates.penalty * pressure:
            self._penalty(side, minute)
        if rng.random() < p.rates.corner_base:
            me.corners += 1
        foul_rate = p.rates.foul * r.discipline / 10
        foul_rate *= math.exp(p.fouls.pressure * (o.attack - r.defence) / 5)
        if rng.random() < foul_rate:
            self._foul(side, minute)

    # ---- chances ---------------------------------------------------------------------------

    def _shot(self, side: str, minute: Minute, xg: float) -> None:
        p = self.params
        me, opp = self.sides[side], self.sides[other(side)]
        me.shots += 1
        me.xg += xg
        shots = p.shots
        on_target = min(shots.on_target_max, shots.on_target_base + shots.on_target_slope * xg)
        if self.rng.random() >= on_target:
            return
        me.on_target += 1
        keeper = math.exp(-p.strength.keeper * (opp.ratings.goalkeeping - 10) / 5)
        if self.rng.random() < min(shots.goal_max, xg / on_target * keeper):
            self._goal(side, minute, xg)

    def _penalty(self, side: str, minute: Minute) -> None:
        me, opp = self.sides[side], self.sides[other(side)]
        outfield = [me.player(pid) for i, pid in me.on_pitch()
                    if me.group_of(i) is not Group.GOALKEEPER]
        if not outfield:
            return
        taker = penalty_order(outfield)[0]
        keeper = goalkeeper_on(opp)
        pen = self.params.penalties
        probability = (pen.conversion * kick_factor(self.params, taker, keeper)
                       / self.params.shootout.base)
        me.shots += 1
        me.xg += pen.xg
        if self.rng.random() < min(pen.conversion_max, probability):
            me.on_target += 1
            me.goals += 1
            self._event(minute, side, "penalty_goal", taker.id, None, pen.xg)
        else:
            if self.rng.random() < pen.miss_saved:  # most misses are saves
                me.on_target += 1
            self._event(minute, side, "penalty_miss", taker.id, None, pen.xg)

    def _goal(self, side: str, minute: Minute, xg: float) -> None:
        p = self.params
        me, opp = self.sides[side], self.sides[other(side)]
        me.goals += 1
        if self.rng.random() < p.rates.own_goal_share:
            weights = [(pid, line_weight(p.weights.own_goal, opp.group_of(i)))
                       for i, pid in opp.on_pitch()]
            culprit = _weighted(self.rng, weights)
            if culprit is not None:  # the shot stays counted: it was deflected in
                self._event(minute, side, "own_goal", culprit)
                return
        header = self.rng.random() < p.scorers.header_share
        weights = []
        for i, pid in me.on_pitch():
            pl, group = me.player(pid), me.group_of(i)
            line = self._line_weight(group)
            if header:
                if group is Group.DEFENDER:
                    line = p.scorers.header_defender_weight
                skill = (_attr(pl, "heading") + _attr(pl, "jumping_reach")) / 2
            else:
                skill = (_attr(pl, "finishing") + _attr(pl, "composure")
                         + _attr(pl, "off_the_ball")) / 3
            weights.append((pid, line * skill * skill))
        scorer = _weighted(self.rng, weights) or me.on_pitch()[0][1]
        assister = None
        if self.rng.random() < p.scorers.assist_share:
            assist_weights = []
            for i, pid in me.on_pitch():
                if pid == scorer:
                    continue
                pl, group = me.player(pid), me.group_of(i)
                line = line_weight(p.weights.assist, group)
                skill = (_attr(pl, "passing") + _attr(pl, "vision") + _attr(pl, "crossing")) / 3
                assist_weights.append((pid, line * skill))
            assister = _weighted(self.rng, assist_weights)
        self._event(minute, side, "goal", scorer, assister, round(xg, 3))

    # ---- discipline --------------------------------------------------------------------------

    def _foul(self, side: str, minute: Minute) -> None:
        p = self.params
        me = self.sides[side]
        me.fouls += 1
        weights = []
        for i, pid in me.on_pitch():
            line = line_weight(p.weights.fouler, me.group_of(i))
            w = line * (me.discipline(pid) / 10) ** p.fouls.fouler_exponent
            if p.caution.enabled and me.yellows.get(pid):
                w *= p.caution.foul
            weights.append((pid, w))
        fouler = _weighted(self.rng, weights)
        if fouler is None:
            return
        proneness = (me.discipline(fouler) / 10) ** p.fouls.card_exponent  # rises steeply
        if self.rng.random() < p.rates.direct_red_per_foul * proneness:
            self._send_off(side, minute, fouler, "red")
            return
        ramp = p.fouls.card_minute_start + p.fouls.card_minute_span * min(minute.base, 90) / 90
        card = p.rates.yellow_per_foul * proneness * ramp
        if p.caution.enabled and me.yellows.get(fouler):
            card *= p.caution.card
        if self.rng.random() < card:
            if me.yellows.get(fouler):
                me.yellows[fouler] = 2
                self._send_off(side, minute, fouler, "second_yellow")
            else:
                me.yellows[fouler] = 1
                self._event(minute, side, "yellow", fouler)
                me.refresh(p)

    def _send_off(self, side: str, minute: Minute, pid: str, kind: str) -> None:
        me = self.sides[side]
        self._event(minute, side, kind, pid)
        slot = next(i for i, x in me.on.items() if x == pid)
        del me.on[slot]
        me.sent_off += 1
        if me.sheet.slot_position(slot) is Position.GK:
            self._replace_keeper(side, minute)
        me.refresh(self.params)

    def _replace_keeper(self, side: str, minute: Minute) -> None:
        """A sent-off keeper: bring on the reserve keeper for an outfield player if possible,
        otherwise an outfield player goes in goal."""
        me = self.sides[side]
        gk_slot = next(i for i in range(len(me.sheet.slot_positions))
                       if me.sheet.slot_position(i) is Position.GK)
        reserve = next((b for b in me.bench if POSITION_GROUP[_best_slot(me.player(b))]
                        is Group.GOALKEEPER), None)
        outfield = sorted(me.on.items(), key=lambda item: (
            item[1] in me.came_on,  # prefer to withdraw a starter
            contribution(me.player(item[1]), me.sheet.slot_position(item[0]), "attack"),
            item[1]))
        if not outfield:
            return
        slot, pid = outfield[0]
        if reserve is not None and me.subs < self.params.subs.max and me.windows < 3:
            me.subs += 1
            me.windows += 1
            me.bench.remove(reserve)
            me.played.add(reserve)
            del me.on[slot]
            me.on[gk_slot] = reserve
            self._event(minute, side, "sub", pid, reserve)
        else:
            del me.on[slot]
            me.on[gk_slot] = pid

    # ---- substitutions ---------------------------------------------------------------------

    def _substitute(self, side: str, minute: Minute, count: int, halftime: bool = False) -> None:
        p = self.params
        me, opp = self.sides[side], self.sides[other(side)]
        if not halftime and me.windows >= 3:
            return
        made = 0
        chasing = me.goals < opp.goals
        for _ in range(count):
            if me.subs >= p.subs.max or not me.bench:
                break
            weights = []
            for i, pid in me.on_pitch():
                group = me.group_of(i)
                if group is Group.GOALKEEPER or pid in me.came_on:
                    continue
                pl = me.player(pid)
                w = line_weight(p.weights.substitution, group)
                w *= (p.subs.stamina_pivot - _attr(pl, "stamina")) / 10
                if me.yellows.get(pid):
                    w *= p.subs.booked_factor
                if chasing and group is Group.DEFENDER:
                    w *= p.subs.chasing_defender_factor
                weights.append((pid, w))
            out = _weighted(self.rng, weights)
            if out is None:
                break
            slot = next(i for i, x in me.on.items() if x == out)
            position = me.sheet.slot_position(slot)
            candidates = [b for b in me.bench
                          if POSITION_GROUP[_best_slot(me.player(b))] is not Group.GOALKEEPER]
            if not candidates:
                break
            incoming = max(candidates, key=lambda b: (_fit(me.player(b), position), b))
            me.bench.remove(incoming)
            me.played.add(incoming)
            me.came_on.add(incoming)
            me.on[slot] = incoming
            me.subs += 1
            made += 1
            self._event(minute, side, "sub", out, incoming)
        if made:
            if not halftime:
                me.windows += 1
            me.refresh(p)

    # ---- output ------------------------------------------------------------------------------

    def report(self, stoppage: tuple[int, int]) -> MatchReport:
        home, away = self.sides[HOME], self.sides[AWAY]
        c_diff = (home.ratings.control - away.ratings.control) / 5
        home_edge = 0.0 if self.neutral else self.params.home.possession
        slope = self.params.home.possession_slope
        home_poss = round(50 + 50 * math.tanh(slope * c_diff + home_edge))
        home_poss = max(20, min(80, home_poss))

        def stats(s: _Side, possession: int) -> SideStats:
            yellows, reds = card_counts(self.events, s.name)
            return SideStats(s.goals, s.shots, s.on_target, round(s.xg, 2), possession,
                             s.corners, s.fouls, yellows, reds)

        def lineup(s: _Side) -> SideLineup:
            sheet = s.sheet
            return SideLineup(sheet.club_id, sheet.formation.name,
                              tuple((sheet.slot_position(i), pid) for i, pid in sheet.starters),
                              sheet.bench, sheet.flags)

        return MatchReport(
            home=stats(home, home_poss), away=stats(away, 100 - home_poss),
            events=tuple(self.events), home_lineup=lineup(home), away_lineup=lineup(away),
            home_finishers=tuple(pid for _, pid in home.on_pitch()),
            away_finishers=tuple(pid for _, pid in away.on_pitch()),
            stoppage=stoppage, model_version=self.params.model_version,
            home_keeper=_id(goalkeeper_on(home)), away_keeper=_id(goalkeeper_on(away)),
        )


def _id(player: Player | None) -> str | None:
    return player.id if player is not None else None


def line_weight(weights: LineWeights, group: Group) -> float:
    return {Group.GOALKEEPER: weights.goalkeeper, Group.DEFENDER: weights.defender,
            Group.MIDFIELDER: weights.midfielder, Group.ATTACKING_MID: weights.attacking_mid,
            Group.FORWARD: weights.forward}[group]


def _fit(player: Player, position: Position) -> int:
    return player.positions[position]


def _best_slot(player: Player) -> Position:
    return max(player.positions.natural_positions() or (Position.MC,),
               key=lambda pos: (player.positions[pos], -pos.order))


def goalkeeper_on(side: _Side) -> Player | None:
    for i, pid in side.on_pitch():
        if side.sheet.slot_position(i) is Position.GK:
            return side.player(pid)
    return None


def penalty_order(players: Sequence[Player]) -> list[Player]:
    """Best penalty takers first (penalty taking, then composure, then id)."""
    return sorted(players, key=lambda p: (-_attr(p, "penalty_taking"), -_attr(p, "composure"),
                                          p.id))


def keeper_skill(keeper: Player | None) -> float:
    if keeper is None:
        return 1.0
    return (_attr(keeper, "reflexes") + _attr(keeper, "agility") + _attr(keeper, "one_on_ones")
            + _attr(keeper, "anticipation")) / 4


def kick_factor(params: ModelParams, taker: Player, keeper: Player | None) -> float:
    """Probability that a shootout kick is scored (research R11)."""
    s = params.shootout
    value = (s.base + s.taker * (_attr(taker, "penalty_taking") - 12)
             + s.composure * (_attr(taker, "composure") - 12)
             - s.keeper * (keeper_skill(keeper) - 12))
    return min(s.high, max(s.low, value))


def simulate_match(home: TeamSheet, away: TeamSheet, players: Mapping[str, Player],
                   params: ModelParams, rng: random.Random,
                   neutral: bool = False) -> tuple[Result, MatchReport]:
    match = _Match(home, away, players, params, rng, neutral)
    stoppage = match.play()
    report = match.report(stoppage)
    result = Result(report.home.goals, report.away.goals, SOURCE,
                    home_red=report.home.reds, away_red=report.away.reds,
                    home_yellow=report.home.yellows, away_yellow=report.away.yellows,
                    report=report)
    return result, report
