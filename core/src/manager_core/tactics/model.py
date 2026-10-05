"""A team's tactic on the FM26 model (spec 006 FR-001, FR-003).

A tactic has an in-possession (IP) and an out-of-possession (OOP) formation, a 7-level mentality,
every team instruction (by phase), an IP and an OOP role plus individual instructions per slot,
and set-piece takers and setups. There are no duties (FM26).
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Set
from dataclasses import asdict, dataclass
from typing import Any

from manager_core.domain.formation import load_catalogue
from manager_core.tactics.catalogue import IP, OOP, load_options, load_roles, suggest_oop


@dataclass(frozen=True, slots=True)
class SlotTactic:
    slot: int  # index in the IP formation
    ip_role: str
    oop_role: str
    instructions: tuple[tuple[str, str], ...] = ()  # player instruction id, setting


@dataclass(frozen=True, slots=True)
class SetPieces:
    takers: tuple[tuple[str, str | None], ...] = ()  # taker id -> player id (None = auto)
    setups: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Tactic:
    ip_formation: str
    oop_formation: str
    mentality: str
    team: tuple[tuple[str, str], ...]  # team instruction id -> setting, sorted
    slots: tuple[SlotTactic, ...]
    set_pieces: SetPieces = SetPieces()
    style: str | None = None  # AI style id, if any

    def setting(self, instruction: str) -> str:
        return dict(self.team)[instruction]


@dataclass(frozen=True, slots=True)
class TacticIssue:
    code: str  # T001 unknown option / T002 role / T003 locked / T004 taker / T005 formation
    path: str


def default_team_instructions() -> tuple[tuple[str, str], ...]:
    return tuple(sorted((o.id, o.default) for o in load_options().team))


def default_tactic(ip_formation: str = "4-4-2", oop_formation: str | None = None,
                   style: str | None = None) -> Tactic:
    formation = load_catalogue()[ip_formation]
    defaults = load_roles().defaults
    options = load_options()
    slots = tuple(SlotTactic(s.index, *defaults[s.position]) for s in formation.slots)
    set_pieces = SetPieces(tuple((t, None) for t in options.takers),
                           tuple((o.id, o.settings[0]) for o in options.setups))
    return Tactic(ip_formation, oop_formation or suggest_oop(ip_formation)[0],
                  options.mentality.default, default_team_instructions(), slots, set_pieces,
                  style)


def validate(tactic: Tactic, squad: Set[str] | None = None) -> list[TacticIssue]:
    issues: list[TacticIssue] = []
    catalogue = load_catalogue()
    options = load_options()
    roles = load_roles().roles
    for path, name in (("ip_formation", tactic.ip_formation),
                       ("oop_formation", tactic.oop_formation)):
        if name not in catalogue:
            issues.append(TacticIssue("T005", path))
    if tactic.mentality not in options.mentality.settings:
        issues.append(TacticIssue("T001", "mentality"))
    given = [option_id for option_id, _ in tactic.team]
    for required in options.team:
        if given.count(required.id) != 1:  # every team instruction exactly once
            issues.append(TacticIssue("T001", f"team.{required.id}"))
    for option_id, setting in tactic.team:
        option = options.team_option(option_id)
        if option is None or setting not in option.settings:
            issues.append(TacticIssue("T001", f"team.{option_id}"))
    if tactic.ip_formation not in catalogue:
        return issues
    formation = catalogue[tactic.ip_formation]
    if sorted(s.slot for s in tactic.slots) != [s.index for s in formation.slots]:
        issues.append(TacticIssue("T002", "slots"))
        return issues
    for slot in tactic.slots:
        position = formation.slots[slot.slot].position
        path = f"slots[{slot.slot}]"
        for phase, role_id in ((IP, slot.ip_role), (OOP, slot.oop_role)):
            role = roles.get(role_id)
            if role is None or role.phase != phase or position not in role.positions:
                issues.append(TacticIssue("T002", f"{path}.{phase}_role"))
        locked: dict[str, str] = {}
        for role_id in (slot.ip_role, slot.oop_role):
            if role_id in roles:
                locked.update(roles[role_id].locked)
        for instr, setting in slot.instructions:
            option = options.player_option(instr)
            if option is None or setting not in option.settings:
                issues.append(TacticIssue("T001", f"{path}.{instr}"))
            elif instr in locked and locked[instr] != setting:
                issues.append(TacticIssue("T003", f"{path}.{instr}"))
    for taker, player_id in tactic.set_pieces.takers:
        if taker not in options.takers:
            issues.append(TacticIssue("T001", f"set_pieces.{taker}"))
        elif player_id is not None and squad is not None and player_id not in squad:
            issues.append(TacticIssue("T004", f"set_pieces.{taker}"))
    for setup, setting in tactic.set_pieces.setups:
        option = options.setup_option(setup)
        if option is None or setting not in option.settings:
            issues.append(TacticIssue("T001", f"set_pieces.{setup}"))
    return issues


def tactic_digest(tactic: Tactic) -> str:
    """A short, stable hash of the full tactic (recorded in match reports)."""
    return hashlib.sha256(repr(asdict(tactic)).encode("utf-8")).hexdigest()[:12]


def for_formation(tactic: Tactic, formation: str) -> tuple[Tactic, tuple[int, ...]]:
    """The tactic refitted to `formation`, and the slots (of the new formation) whose roles and
    instructions were reset (spec 006 edge case).

    Mentality, team instructions and set pieces are kept. Each new slot takes the roles and
    player instructions of an old slot at the same position (in slot order), if they are still
    valid there; the other slots get the position's default roles. The OOP formation is kept if
    it is still one of the suggestions for the new shape."""
    if tactic.ip_formation == formation:
        return tactic, ()
    catalogue = load_catalogue()
    base = default_tactic(formation)
    old_positions = catalogue[tactic.ip_formation].slots if tactic.ip_formation in catalogue \
        else ()
    unused = {s.slot: s for s in tactic.slots}
    slots, changed = [], []
    for new_slot, slot_def in zip(base.slots, catalogue[formation].slots, strict=True):
        match = next((unused[o.index] for o in old_positions
                      if o.index in unused and o.position is slot_def.position), None)
        kept = None
        if match is not None:
            kept = SlotTactic(new_slot.slot, match.ip_role, match.oop_role, match.instructions)
            probe = dataclasses.replace(base, slots=tuple(
                kept if s.slot == new_slot.slot else s for s in base.slots))
            if any(i.path.startswith(f"slots[{new_slot.slot}]") for i in validate(probe)):
                kept = None
            else:
                del unused[match.slot]
        if kept is None:
            changed.append(new_slot.slot)
        slots.append(kept or new_slot)
    oop = tactic.oop_formation if tactic.oop_formation in suggest_oop(formation) \
        else base.oop_formation
    return (Tactic(formation, oop, tactic.mentality, tactic.team, tuple(slots),
                   tactic.set_pieces, tactic.style), tuple(changed))


def dropped_choices(tactic: Tactic, formation: str) -> tuple[int, ...]:
    """Old slots whose own choices (non-default roles, or player instructions) are lost when
    the tactic is refitted to `formation`: the slots that were not carried over and were not
    just defaults. Only these are worth telling the owner about."""
    if tactic.ip_formation == formation:
        return ()
    refitted, _ = for_formation(tactic, formation)
    old_formation = load_catalogue()[tactic.ip_formation]
    defaults = load_roles().defaults
    kept = list(refitted.slots)
    dropped = []
    for slot in tactic.slots:
        same = next((k for k in kept if (k.ip_role, k.oop_role, k.instructions)
                     == (slot.ip_role, slot.oop_role, slot.instructions)), None)
        if same is not None:
            kept.remove(same)
            continue
        position = old_formation.slots[slot.slot].position
        if (slot.ip_role, slot.oop_role) != tuple(defaults[position]) or slot.instructions:
            dropped.append(slot.slot)
    return tuple(dropped)


def tactic_to_json(tactic: Tactic) -> dict[str, Any]:
    return {
        "ip_formation": tactic.ip_formation, "oop_formation": tactic.oop_formation,
        "mentality": tactic.mentality, "team": [list(x) for x in tactic.team],
        "slots": [{"slot": s.slot, "ip_role": s.ip_role, "oop_role": s.oop_role,
                   "instructions": [list(x) for x in s.instructions]} for s in tactic.slots],
        "takers": [list(x) for x in tactic.set_pieces.takers],
        "setups": [list(x) for x in tactic.set_pieces.setups],
        "style": tactic.style,
    }


def tactic_from_json(d: dict[str, Any]) -> Tactic:
    return Tactic(
        d["ip_formation"], d["oop_formation"], d["mentality"],
        tuple((a, b) for a, b in d["team"]),
        tuple(SlotTactic(s["slot"], s["ip_role"], s["oop_role"],
                         tuple((a, b) for a, b in s["instructions"])) for s in d["slots"]),
        SetPieces(tuple((a, b) for a, b in d["takers"]), tuple((a, b) for a, b in d["setups"])),
        d["style"])
