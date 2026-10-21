"""The assistant's suggestions (spec 010): the opposition report, and advice on the selection,
the tactic and the squad. FM's assistant manager is the model. Every suggestion is only that
(Constitution V): an action, when there is one, is applied by the client through the same
methods as a change by hand.

The opponent is read with the AI's own code (spec 006): its style, its team sheet and the
strength figure `tactics.ai.pre_match` adapts to. The tactic advice is that adaptation applied
to the owner's tactic: what the AI would do in his place.
"""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib import resources
from typing import Any

from manager_core.career.career import Career
from manager_core.career.discipline import YELLOWS_PER_BAN, Discipline
from manager_core.career.selection import Selection, propose, to_team_sheet
from manager_core.competition.season import Match
from manager_core.domain.player import Player
from manager_core.domain.positions import NATURAL_THRESHOLD, Position
from manager_core.i18n import t
from manager_core.quicksim.squad import TeamSheet
from manager_core.ratings.ability import current_ability
from manager_core.ratings.suitability import suitability_milli
from manager_core.tactics import ai
from manager_core.tactics import catalogue as tactics_catalogue
from manager_core.tactics.model import Tactic, with_role

WARNING = "warning"
INFO = "info"


@cache
def params() -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("career").joinpath(
        "assistant.toml")
    return tomllib.loads(entry.read_text("utf-8"))


@dataclass(frozen=True, slots=True)
class Advice:
    kind: str
    severity: str  # info / warning
    text: str
    action: dict[str, Any] | None = None  # swap {slot, player_id} / role {slot, phase, role_id}
    # / tactic {tactic}


@dataclass(frozen=True, slots=True)
class KeyPlayer:
    player_id: str
    name: str
    position: str


@dataclass(frozen=True, slots=True)
class OppositionReport:
    match_id: str
    opponent_id: str
    opponent_name: str
    home: bool  # the owner's club plays at home
    neutral: bool
    style: str
    style_label: str
    formation: str
    band: str  # favourite / even / underdog, for the owner's club
    key_players: tuple[KeyPlayer, ...]
    top_scorers: tuple[tuple[str, int], ...]  # (name, goals) before the report's day
    form: tuple[str, ...]  # V / E / D, the latest last
    suspended: tuple[str, ...]  # names
    text: str


@dataclass(frozen=True, slots=True)
class Briefing:
    report: OppositionReport | None
    selection: tuple[Advice, ...]
    tactic: tuple[Advice, ...]
    squad: tuple[Advice, ...]


# ---- helpers ---------------------------------------------------------------------------------


def next_user_match(career: Career) -> Match | None:
    club = career.user_club_id
    return next((m for m in career.season.sorted_matches()
                 if m.id not in career.season.results and club in (m.home_id, m.away_id)),
                None)


def _discipline(career: Career) -> Discipline | None:
    ledger = career.season.discipline
    return ledger if isinstance(ledger, Discipline) else None


def _suspended(career: Career, club_id: str) -> frozenset[str]:
    ledger = _discipline(career)
    return ledger.suspended(club_id) if ledger is not None else frozenset()


def _selection(career: Career, shown: Selection | None = None) -> Selection:
    """The selection advised on: the one on screen, else the kept one, else the assistant's."""
    if shown is not None:
        return shown
    if isinstance(career.selection, Selection):
        return career.selection
    return propose(career)


def _user_sheet(career: Career, selection: Selection) -> TeamSheet:
    return to_team_sheet(career, selection)


def _opponent_sheet(career: Career, opponent: str) -> TeamSheet:
    return career.live_provider.team_sheet(opponent, _suspended(career, opponent))


def _pos(position: Position | str) -> str:
    return t(f"pos.{Position(position).value}")


def _band(own: float, opponent: float) -> str:
    rules = ai.styles_table()["adaptation"]
    ratio = own / max(1.0, opponent)
    if ratio < rules["big_underdog"]:
        return "underdog"
    if ratio > rules["big_favourite"]:
        return "favourite"
    return "even"


def _setting_label(option: tactics_catalogue.OptionDef, setting: str) -> str:
    return option.labels[option.settings.index(setting)]


# ---- the opposition report (US1) -------------------------------------------------------------


def _played_before(career: Career, club: str, day: date) -> list[Match]:
    season = career.season
    return [m for m in season.sorted_matches()
            if m.id in season.results and club in (m.home_id, m.away_id)
            and m.kickoff.date() < day]


def _form(career: Career, club: str, day: date) -> tuple[str, ...]:
    out = []
    for m in _played_before(career, club, day)[-int(params()["form_matches"]):]:
        r = career.season.results[m.id]
        own, other = ((r.home_goals, r.away_goals) if m.home_id == club
                      else (r.away_goals, r.home_goals))
        out.append("V" if own > other else "E" if own == other else "D")
    return tuple(out)


def _scorers(career: Career, club: str, day: date) -> tuple[tuple[str, int], ...]:
    goals: dict[str, int] = {}
    for m in _played_before(career, club, day):
        report = career.season.results[m.id].report
        if report is None:
            continue
        side = "home" if m.home_id == club else "away"
        for e in report.events:
            if e.kind in ("goal", "penalty_goal") and e.side == side:
                goals[e.player_id] = goals.get(e.player_id, 0) + 1
    ranked = sorted(goals, key=lambda pid: (-goals[pid], pid))[:int(params()["top_scorers"])]
    return tuple((career.season.dataset.player(pid).display_name, goals[pid]) for pid in ranked)


def opposition_report(career: Career, match_id: str, as_of: date | None = None,
                      with_suspensions: bool = True) -> OppositionReport:
    """The opponent of this user match, as of a day (form and scorers count the matches before
    it; the default is the match day). Suspensions are today's, so a report for an earlier day
    leaves them out (`with_suspensions`)."""
    season = career.season
    match = season.matches[match_id]
    club = career.user_club_id
    home = match.home_id == club
    opponent = match.away_id if home else match.home_id
    day = as_of or match.kickoff.date()
    neutral = season._context(match).neutral
    players = season.dataset.players
    theirs = _opponent_sheet(career, opponent)
    ours = _user_sheet(career, _selection(career))
    band = _band(ai.strength(ours, players), ai.strength(theirs, players))
    style = career.live_provider.styles()[opponent]
    style_label = str(ai.styles_table()["styles"][style]["label"])
    starters = [(theirs.slot_position(i), players[pid]) for i, pid in theirs.starters]
    starters.sort(key=lambda item: (-current_ability(item[1]), item[1].id))
    key = tuple(KeyPlayer(p.id, p.display_name, _pos(pos))
                for pos, p in starters[:int(params()["key_players"])])
    scorers = _scorers(career, opponent, day)
    form = _form(career, opponent, day)
    suspended = tuple(sorted(season.dataset.player(pid).display_name
                             for pid in _suspended(career, opponent))) if with_suspensions else ()
    name = season.club_name(opponent)
    parts = [t("assistant.report.head", opponent=name, style=style_label,
               formation=theirs.formation.name),
             t(f"assistant.report.band.{band}")]
    parts.append(t("assistant.report.key", players=", ".join(
        f"{k.name} ({k.position})" for k in key)))
    parts.append(t("assistant.report.form", form=" ".join(form)) if form
                 else t("assistant.report.no_form"))
    if scorers:
        parts.append(t("assistant.report.scorers", scorers=", ".join(
            t("assistant.report.scorer", name=n, goals=g) for n, g in scorers)))
    if suspended:
        parts.append(t("assistant.report.suspended", players=", ".join(suspended)))
    return OppositionReport(match_id, opponent, name, home, neutral, style, style_label,
                            theirs.formation.name, band, key, scorers, form, suspended,
                            " ".join(parts))


# ---- the selection (US2) ---------------------------------------------------------------------


def selection_advice(career: Career, selection: Selection) -> list[Advice]:
    world = career.world
    positions = [s.position for s in _formation(selection.formation).slots]
    starters = dict(selection.starters)
    out_ids = _suspended(career, career.user_club_id)
    squad = sorted((p for p in world.squad(career.user_club_id) if p.id not in out_ids),
                   key=lambda p: p.id)
    others = [p for p in squad if p.id not in starters.values()]
    advice: list[Advice] = []
    ledger = _discipline(career)
    if ledger is not None:
        for _slot, pid in sorted(starters.items()):
            if ledger.yellows(pid) == YELLOWS_PER_BAN - 1:
                advice.append(Advice("one_from_ban", WARNING, t(
                    "assistant.selection.one_from_ban", player=world.player(pid).display_name)))
    swaps: list[tuple[float, Advice]] = []
    margin = float(params()["better_on_bench"])
    for slot, pid in sorted(starters.items()):
        position = positions[slot]
        starter = world.player(pid)
        score = suitability_milli(starter, position)
        natural = [p for p in others if p.positions[position] >= NATURAL_THRESHOLD]
        best = max(natural, key=lambda p: (suitability_milli(p, position), p.id), default=None)
        action = ({"type": "swap", "slot": slot, "player_id": best.id}
                  if best is not None else None)
        if starter.positions[position] < NATURAL_THRESHOLD:
            text = t("assistant.selection.out_of_position", player=starter.display_name,
                     position=_pos(position))
            if best is not None:
                text += " " + t("assistant.selection.try", player=best.display_name)
            advice.append(Advice("out_of_position", WARNING, text, action))
        elif best is not None and suitability_milli(best, position) >= score * (1 + margin):
            gain = suitability_milli(best, position) / max(1, score)
            swaps.append((gain, Advice("better_option", INFO, t(
                "assistant.selection.better", player=best.display_name,
                starter=starter.display_name, position=_pos(position)), action)))
    swaps.sort(key=lambda item: -item[0])
    advice += [a for _, a in swaps[:int(params()["max_swaps"])]]
    return advice


def _formation(name: str) -> Any:
    from manager_core.domain.formation import load_catalogue
    return load_catalogue()[name]


# ---- the tactic (US3) ------------------------------------------------------------------------


def _describe(before: Tactic, after: Tactic) -> list[str]:
    options = tactics_catalogue.load_options()
    changes = []
    if before.mentality != after.mentality:
        changes.append(t("assistant.tactic.change", option=options.mentality.label,
                         setting=_setting_label(options.mentality, after.mentality)))
    old, new = dict(before.team), dict(after.team)
    for key in sorted(new):
        if old.get(key) != new[key]:
            option = options.team_option(key)
            if option is not None:
                changes.append(t("assistant.tactic.change", option=option.label,
                                 setting=_setting_label(option, new[key])))
    return changes


def tactic_advice(career: Career, tactic: Tactic, match_id: str,
                  shown: Selection | None = None) -> list[Advice]:
    season = career.season
    match = season.matches[match_id]
    home = match.home_id == career.user_club_id
    opponent = match.away_id if home else match.home_id
    players = season.dataset.players
    selection = _selection(career, shown)
    own = ai.strength(_user_sheet(career, selection), players)
    theirs = ai.strength(_opponent_sheet(career, opponent), players)
    advice: list[Advice] = []
    adapted = ai.pre_match(dataclasses.replace(tactic, style=None), own, theirs, home=home,
                           neutral=season._context(match).neutral)
    changes = _describe(tactic, adapted)
    if changes:
        advice.append(Advice("adapt", INFO, t(
            f"assistant.tactic.adapt.{_band(own, theirs)}", changes="; ".join(changes)),
            {"type": "tactic", "tactic": adapted}))
    starters = dict(selection.starters)
    positions = [s.position for s in _formation(tactic.ip_formation).slots]
    roles = tactics_catalogue.load_roles().roles
    gain = float(params()["role_gain"])
    found: list[tuple[float, Advice]] = []
    for slot in tactic.slots:
        pid = starters.get(slot.slot)
        if pid is None or slot.slot >= len(positions):
            continue
        player: Player = players[pid]
        current = tactics_catalogue.role_suitability(player, roles[slot.ip_role])
        options = tactics_catalogue.valid_roles(positions[slot.slot], "ip")
        best = max(options, key=lambda r: (tactics_catalogue.role_suitability(player, r), r.id),
                   default=None)
        if best is None or best.id == slot.ip_role:
            continue
        better = tactics_catalogue.role_suitability(player, best)
        if better - current >= gain:
            found.append((better - current, Advice("role", INFO, t(
                "assistant.tactic.role", player=player.display_name, role=best.label,
                current=roles[slot.ip_role].label),
                {"type": "role", "slot": slot.slot, "phase": "ip", "role_id": best.id})))
    found.sort(key=lambda item: -item[0])
    advice += [a for _, a in found[:int(params()["max_roles"])]]
    return advice


def apply_role(tactic: Tactic, action: dict[str, Any]) -> Tactic:
    return with_role(tactic, int(action["slot"]), str(action["phase"]), str(action["role_id"]))


# ---- the squad (US4) -------------------------------------------------------------------------


def squad_advice(career: Career) -> list[Advice]:
    world = career.world
    today = career.current_date
    squad = sorted(world.squad(career.user_club_id), key=lambda p: p.id)
    advice: list[Advice] = []
    for line, spec in params()["cover"].items():
        positions = [Position(p) for p in spec["positions"]]
        count = sum(1 for p in squad if any(p.positions[pos] >= NATURAL_THRESHOLD
                                            for pos in positions))
        if count < int(spec["need"]):
            advice.append(Advice("cover", WARNING, t(
                "assistant.squad.cover", line=t(f"assistant.line.{line}"), count=count,
                need=spec["need"])))
    chosen = _selection(career)  # the owner's XI (the assistant's until he picks one)
    positions = [s.position for s in _formation(chosen.formation).slots]
    xi = {pid: positions[slot] for slot, pid in chosen.starters}
    for pid in sorted(xi):
        player = world.player(pid)
        if player.age(today) >= int(params()["ageing_age"]):
            advice.append(Advice("ageing", INFO, t(
                "assistant.squad.ageing", player=player.display_name, age=player.age(today))))
    # ready: out of the XI, and at his best natural position at least as good as the XI's
    # median starter is at his own
    scores = sorted(suitability_milli(world.player(pid), pos) for pid, pos in xi.items())
    median = scores[len(scores) // 2] if scores else 0
    for player in squad:
        if player.id in xi or player.age(today) > int(params()["youth_age"]):
            continue
        natural = [pos for pos in Position if player.positions[pos] >= NATURAL_THRESHOLD]
        best = max(natural, key=lambda pos: (suitability_milli(player, pos), -pos.order),
                   default=None)
        if best is not None and suitability_milli(player, best) >= median:
            advice.append(Advice("youth_ready", INFO, t(
                "assistant.squad.youth", player=player.display_name, age=player.age(today),
                position=_pos(best))))
    return advice


# ---- the briefing ----------------------------------------------------------------------------


def briefing(career: Career, tactic: Tactic, shown: Selection | None = None) -> Briefing:
    """`shown`: the selection on the owner's screen, when it is not kept yet."""
    match = next_user_match(career)
    selection = _selection(career, shown)
    return Briefing(
        opposition_report(career, match.id) if match is not None else None,
        tuple(selection_advice(career, selection)),
        tuple(tactic_advice(career, tactic, match.id, selection)) if match is not None else (),
        tuple(squad_advice(career)))
