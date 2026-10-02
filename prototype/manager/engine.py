"""Minute-by-minute match engine.

Each minute one duel happens: an attacker from the team in possession vs a
defender from the other team. The duel can end in a foul (possibly a card or a
penalty), a won tackle, or the attacker getting through to a shot.

Player behaviour reacts to match state. The first such behaviour is card
caution: a booked player eases off his tackles so he is less likely to commit
a foul (and see a second yellow), at the cost of losing more duels. How much he
holds back depends on his composure and aggression.

The engine is deterministic for a given seed, so any match can be replayed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .models import Mentality, Player, Position, Team

MAX_SUBS = 5

# Calibration constants (tuned with calibrate.py: ~2.5 goals, ~24 fouls, ~4 yellows per match).
BASE_FOUL = 0.24          # chance a duel ends in a foul for an average player
YELLOW_PER_FOUL = 0.19
STRAIGHT_RED_PER_FOUL = 0.002
PENALTY_PER_FOUL = 0.012
SHOT_ON_WIN = 0.66        # chance the attacker gets a shot after winning the duel
BASE_XG = 0.10
PENALTY_XG = 0.76
HOME_ADVANTAGE = 1.12  # applied to possession and to the home side's duels

# How a fully cautious player changes: fouls drop by 85%, tackling power drops by 25%.
CAUTION_FOUL_REDUCTION = 0.85
CAUTION_TACKLE_PENALTY = 0.25

ATTACK_MULT = {Mentality.DEFENSIVE: 0.92, Mentality.BALANCED: 1.0, Mentality.ATTACKING: 1.08}
DEFENSE_MULT = {Mentality.DEFENSIVE: 1.08, Mentality.BALANCED: 1.0, Mentality.ATTACKING: 0.94}

DUEL_ATTACKER_WEIGHT = {Position.GK: 0.0, Position.DF: 0.6, Position.MF: 2.0, Position.FW: 2.0}
DUEL_DEFENDER_WEIGHT = {Position.GK: 0.0, Position.DF: 2.0, Position.MF: 1.5, Position.FW: 0.3}
SHOOTER_WEIGHT = {Position.GK: 0.0, Position.DF: 0.4, Position.MF: 1.5, Position.FW: 3.0}


@dataclass
class PlayerState:
    player: Player
    energy: float = 100.0
    on_pitch: bool = True
    yellow: bool = False
    sent_off: bool = False
    goals: int = 0
    shots: int = 0
    fouls: int = 0
    tackles_won: int = 0
    tackles_lost: int = 0

    def energy_factor(self) -> float:
        return 0.75 + 0.25 * self.energy / 100


@dataclass
class Event:
    minute: str
    kind: str          # goal, shot_saved, shot_wide, foul, yellow, second_yellow, red, penalty, sub, caution, whistle
    side: str | None   # "home" / "away"
    player: str | None
    text: str


@dataclass
class TeamState:
    team: Team
    side: str
    lineup: list[PlayerState]
    bench: list[PlayerState]
    goals: int = 0
    subs_used: int = 0
    all_states: list[PlayerState] = field(default_factory=list)

    def on_pitch(self) -> list[PlayerState]:
        return [p for p in self.lineup if p.on_pitch]

    def outfield(self) -> list[PlayerState]:
        return [p for p in self.on_pitch() if p.player.position is not Position.GK]

    def goalkeeper(self) -> PlayerState | None:
        return next((p for p in self.on_pitch() if p.player.position is Position.GK), None)


def caution_level(ps: PlayerState, card_caution_enabled: bool) -> float:
    """0 = plays normally, ~0.9 = very careful. Only booked players hold back."""
    if not card_caution_enabled or not ps.yellow:
        return 0.0
    p = ps.player
    level = 0.45 + 0.5 * p.composure / 20 - 0.2 * (p.aggression - 10) / 10
    return max(0.0, min(0.9, level))


class Match:
    def __init__(self, home: Team, away: Team, seed: int | None = None):
        if len(home.players) < 11 or len(away.players) < 11:
            raise ValueError("Each team needs at least 11 players")
        self.rng = random.Random(seed)
        self.seed = seed
        self.home = self._team_state(home, "home")
        self.away = self._team_state(away, "away")
        self.events: list[Event] = []
        first_half_extra = self.rng.randint(0, 3)
        second_half_extra = self.rng.randint(1, 6)
        self._ticks = [str(m) for m in range(1, 46)] + [f"45+{i}" for i in range(1, first_half_extra + 1)]
        self._ticks += [str(m) for m in range(46, 91)] + [f"90+{i}" for i in range(1, second_half_extra + 1)]
        self._tick_index = 0
        self._log("0", "whistle", None, None, f"Começa o jogo: {home.name} x {away.name}!")

    @staticmethod
    def _team_state(team: Team, side: str) -> TeamState:
        lineup = [PlayerState(p) for p in team.starters]
        bench = [PlayerState(p, on_pitch=False) for p in team.bench]
        return TeamState(team, side, lineup, bench, all_states=lineup + bench)

    # ---- public API ----------------------------------------------------

    @property
    def finished(self) -> bool:
        return self._tick_index >= len(self._ticks)

    @property
    def minute(self) -> str:
        return self._ticks[min(self._tick_index, len(self._ticks) - 1)]

    @property
    def score(self) -> tuple[int, int]:
        return self.home.goals, self.away.goals

    def step(self) -> list[Event]:
        """Play one minute; returns the events of that minute."""
        if self.finished:
            return []
        start = len(self.events)
        minute = self._ticks[self._tick_index]
        if minute == "46":
            self._log(minute, "whistle", None, None, "Começa o segundo tempo.")
        self._play_minute(minute)
        self._drain_energy()
        self._tick_index += 1
        if minute.startswith("45") and (self._tick_index < len(self._ticks) and self._ticks[self._tick_index] == "46"):
            self._log(minute, "whistle", None, None, f"Fim do primeiro tempo: {self._score_text()}")
        if self.finished:
            self._log(minute, "whistle", None, None, f"Fim de jogo: {self._score_text()}")
        return self.events[start:]

    def simulate(self) -> list[Event]:
        while not self.finished:
            self.step()
        return self.events

    def substitute(self, side: str, out_name: str, in_name: str) -> None:
        ts = self.home if side == "home" else self.away
        if ts.subs_used >= MAX_SUBS:
            raise ValueError("No substitutions left")
        out_ps = next((p for p in ts.on_pitch() if p.player.name == out_name), None)
        in_ps = next((p for p in ts.bench if p.player.name == in_name and not p.on_pitch), None)
        if out_ps is None or in_ps is None:
            raise ValueError("Invalid substitution")
        out_ps.on_pitch = False
        in_ps.on_pitch = True
        ts.bench.remove(in_ps)
        ts.lineup[ts.lineup.index(out_ps)] = in_ps
        ts.subs_used += 1
        self._log(self.minute, "sub", side, in_name, f"Substituição no {ts.team.name}: sai {out_name}, entra {in_name}.")

    # ---- simulation ----------------------------------------------------

    def _play_minute(self, minute: str) -> None:
        attacking, defending = self._possession()
        attacker = self._pick(attacking.outfield(), DUEL_ATTACKER_WEIGHT)
        defender = self._pick(defending.outfield(), DUEL_DEFENDER_WEIGHT)
        if attacker is None or defender is None:
            return
        caution = caution_level(defender, defending.team.tactic.card_caution)

        p_foul = BASE_FOUL * (defender.player.aggression / 10) * (1 - CAUTION_FOUL_REDUCTION * caution)
        p_foul *= 1 + 0.5 * (1 - defender.energy / 100)  # tired players arrive late
        if self.rng.random() < p_foul:
            self._foul(minute, attacking, defending, attacker, defender)
            return

        atk = (attacker.player.passing + attacker.player.pace + attacker.player.finishing) / 3
        atk *= attacker.energy_factor() * ATTACK_MULT[attacking.team.tactic.mentality]
        if attacking is self.home:
            atk *= HOME_ADVANTAGE
        dfn = (defender.player.tackling * (1 - CAUTION_TACKLE_PENALTY * caution) + defender.player.positioning) / 2
        dfn *= defender.energy_factor() * DEFENSE_MULT[defending.team.tactic.mentality]
        dfn *= self._numbers_factor(defending, attacking)
        if defending is self.home:
            dfn *= HOME_ADVANTAGE

        if self.rng.random() < dfn / (atk + dfn):
            defender.tackles_won += 1
            return
        defender.tackles_lost += 1
        if self.rng.random() < SHOT_ON_WIN * ATTACK_MULT[attacking.team.tactic.mentality]:
            shooter = self._pick(attacking.outfield(), SHOOTER_WEIGHT, bias=lambda p: p.player.finishing)
            self._shot(minute, attacking, defending, shooter, penalty=False)

    def _possession(self) -> tuple[TeamState, TeamState]:
        def control(ts: TeamState) -> float:
            return sum(
                (p.player.passing * 0.6 + p.player.pace * 0.2 + p.player.positioning * 0.2) * p.energy_factor()
                for p in ts.outfield()
            )
        h = control(self.home) * HOME_ADVANTAGE
        a = control(self.away)
        if self.rng.random() < h / (h + a):
            return self.home, self.away
        return self.away, self.home

    @staticmethod
    def _numbers_factor(ts: TeamState, other: TeamState) -> float:
        """A team down to 10 men defends worse (more space)."""
        diff = len(ts.on_pitch()) - len(other.on_pitch())
        return 1 + 0.06 * diff

    def _foul(self, minute, attacking: TeamState, defending: TeamState, attacker: PlayerState, defender: PlayerState):
        defender.fouls += 1
        name = defender.player.name
        penalty = self.rng.random() < PENALTY_PER_FOUL
        severity = defender.player.aggression / 10 * (1.6 if penalty else 1.0)
        roll = self.rng.random()
        if penalty:
            self._log(minute, "penalty", attacking.side, attacker.player.name,
                      f"PÊNALTI! {name} derruba {attacker.player.name} na área.")
        else:
            self._log(minute, "foul", defending.side, name, f"Falta de {name} em {attacker.player.name}.")

        if roll < STRAIGHT_RED_PER_FOUL * severity:
            self._send_off(minute, defending, defender, "red", f"VERMELHO DIRETO para {name}!")
        elif roll < (STRAIGHT_RED_PER_FOUL + YELLOW_PER_FOUL) * severity:
            if defender.yellow:
                self._send_off(minute, defending, defender, "second_yellow", f"Segundo amarelo para {name}. Expulso!")
            else:
                defender.yellow = True
                self._log(minute, "yellow", defending.side, name, f"Cartão amarelo para {name}.")
                if caution_level(defender, defending.team.tactic.card_caution) >= 0.5:
                    self._log(minute, "caution", defending.side, name,
                              f"{name} está pendurado e passa a dar o bote com mais cuidado.")

        if penalty:
            taker = max(attacking.outfield(), key=lambda p: p.player.finishing)
            self._shot(minute, attacking, defending, taker, penalty=True)

    def _send_off(self, minute, ts: TeamState, ps: PlayerState, kind: str, text: str) -> None:
        ps.sent_off = True
        ps.on_pitch = False
        self._log(minute, kind, ts.side, ps.player.name, text)

    def _shot(self, minute, attacking: TeamState, defending: TeamState, shooter: PlayerState, penalty: bool):
        shooter.shots += 1
        gk = defending.goalkeeper()
        gk_skill = gk.player.goalkeeping * gk.energy_factor() if gk else 3
        fin = shooter.player.finishing * shooter.energy_factor()
        base = PENALTY_XG if penalty else BASE_XG
        xg = base * (fin / 10) / (gk_skill / 10) ** 0.8
        xg = max(0.02, min(0.92 if penalty else 0.45, xg))
        name = shooter.player.name
        if self.rng.random() < xg:
            shooter.goals += 1
            attacking.goals += 1
            self._log(minute, "goal", attacking.side, name, f"GOOOL do {attacking.team.name}! {name} marca. {self._score_text()}")
        elif self.rng.random() < 0.4:
            keeper = gk.player.name if gk else "a defesa"
            self._log(minute, "shot_saved", attacking.side, name, f"{name} finaliza, {keeper} defende.")
        else:
            self._log(minute, "shot_wide", attacking.side, name, f"{name} chuta para fora.")

    def _drain_energy(self) -> None:
        for ts in (self.home, self.away):
            for p in ts.on_pitch():
                p.energy = max(0.0, p.energy - (0.25 + (20 - p.player.stamina) * 0.02))

    def _pick(self, players: list[PlayerState], weights: dict, bias=None) -> PlayerState | None:
        w = [weights[p.player.position] * (bias(p) if bias else 1) for p in players]
        if not players or sum(w) == 0:
            return None
        return self.rng.choices(players, weights=w)[0]

    def _log(self, minute, kind, side, player, text) -> None:
        self.events.append(Event(minute, kind, side, player, text))

    def _score_text(self) -> str:
        return f"{self.home.team.name} {self.home.goals} x {self.away.goals} {self.away.team.name}"
