"""The tactic model on FM26 (spec 006 FR-001..FR-003)."""

import dataclasses

import pytest

from manager_core.domain.formation import load_catalogue
from manager_core.domain.positions import Position
from manager_core.tactics.catalogue import (
    load_options,
    load_roles,
    role_suitability,
    suggest_oop,
    valid_roles,
)
from manager_core.tactics.model import (
    SlotTactic,
    Tactic,
    TacticIssue,
    default_tactic,
    validate,
)
from tests.helpers import attrs, player


def _codes(tactic: Tactic, squad: set[str] | None = None) -> list[str]:
    return [i.code for i in validate(tactic, squad)]


def test_option_set_is_fm26() -> None:
    options = load_options()
    assert len(options.mentality.settings) == 7
    assert len(options.team) == 32  # FM26: 20 in possession + 12 out of possession
    assert len(options.player) == 14  # FM26: 10 in possession + 4 out of possession
    assert {o.phase for o in options.team} == {
        "ip_overview", "ip_build_up", "ip_progression", "ip_final_third", "oop_overview",
        "oop_high_press", "oop_mid_block", "oop_low_block"}
    for option in options.team:
        assert option.default in option.settings
        assert len(option.labels) == len(option.settings)


def test_roles_cover_every_position_in_both_phases() -> None:
    roles = load_roles()
    assert len(roles.roles) >= 70
    for position in Position:
        assert valid_roles(position, "ip"), position
        assert valid_roles(position, "oop"), position
    for role in roles.roles.values():
        assert role.key and all(w > 0 for w in role.key.values())
        options = {o.id: o for o in load_options().player}
        for instr, setting in role.locked.items():
            assert setting in options[instr].settings, (role.id, instr)


def test_default_tactic_is_valid_for_every_formation() -> None:
    for name in load_catalogue():
        tactic = default_tactic(name)
        assert _codes(tactic) == [], name
        assert tactic.oop_formation == suggest_oop(name)[0]


def test_oop_suggestions_are_three_catalogue_formations() -> None:
    catalogue = load_catalogue()
    for name in catalogue:
        suggestions = suggest_oop(name)
        assert len(suggestions) == 3 and all(s in catalogue for s in suggestions)
    assert suggest_oop("4-3-3")[0] == "4-1-4-1"  # FM26's own example


def test_validation_codes() -> None:
    base = default_tactic("4-3-3")
    assert "T005" in _codes(dataclasses.replace(base, oop_formation="9-9-9"))
    assert "T001" in _codes(dataclasses.replace(base, mentality="crazy"))
    team = dict(base.team)
    team["tempo"] = "warp"
    assert "T001" in _codes(dataclasses.replace(base, team=tuple(sorted(team.items()))))
    slots = list(base.slots)
    st_slot = next(i for i, s in enumerate(slots) if s.ip_role == "centre_forward")
    slots[st_slot] = dataclasses.replace(slots[st_slot], ip_role="goalkeeper")
    assert "T002" in _codes(dataclasses.replace(base, slots=tuple(slots)))
    slots = list(base.slots)
    slots[st_slot] = SlotTactic(slots[st_slot].slot, "poacher", "centre_forward_oop",
                                (("hold_up_ball", "yes"),))  # Poacher locks hold up ball: no
    assert "T003" in _codes(dataclasses.replace(base, slots=tuple(slots)))
    takers = dict(base.set_pieces.takers)
    takers["penalties"] = "p-nobody"
    sp = dataclasses.replace(base.set_pieces, takers=tuple(sorted(takers.items())))
    assert "T004" in _codes(dataclasses.replace(base, set_pieces=sp), squad={"p-1"})


def test_role_suitability_follows_key_attributes() -> None:
    roles = load_roles().roles
    finisher = player("p-a", positions={Position.ST: 20},
                      attributes=attrs(8, finishing=19, anticipation=18, off_the_ball=18,
                                       composure=17))
    target = player("p-b", positions={Position.ST: 20},
                    attributes=attrs(8, heading=19, jumping_reach=19, strength=19, bravery=17))
    assert role_suitability(finisher, roles["poacher"]) > role_suitability(
        target, roles["poacher"])
    assert role_suitability(target, roles["target_forward"]) > role_suitability(
        finisher, roles["target_forward"])
    assert 1 <= role_suitability(finisher, roles["poacher"]) <= 20


@pytest.mark.parametrize("formation", ["4-4-2", "3-5-2"])
def test_default_roles_follow_positions(formation: str) -> None:
    tactic = default_tactic(formation)
    positions = [s.position for s in load_catalogue()[formation].slots]
    defaults = load_roles().defaults
    for slot, pos in zip(tactic.slots, positions, strict=True):
        assert (slot.ip_role, slot.oop_role) == defaults[pos]


def test_missing_or_duplicate_team_instruction_is_t001() -> None:
    base = default_tactic("4-4-2")
    missing = dataclasses.replace(base, team=base.team[1:])
    assert TacticIssue("T001", f"team.{base.team[0][0]}") in validate(missing)
    duplicate = dataclasses.replace(base, team=(*base.team, base.team[0]))
    assert TacticIssue("T001", f"team.{base.team[0][0]}") in validate(duplicate)


def test_a_new_formation_keeps_the_slots_that_still_fit() -> None:
    from manager_core.tactics.catalogue import valid_roles
    from manager_core.tactics.model import for_formation

    catalogue = load_catalogue()
    old = default_tactic("4-4-2")
    slots = []
    for slot in old.slots:
        position = catalogue["4-4-2"].slots[slot.slot].position
        ip = [r.id for r in valid_roles(position, "ip")]
        slots.append(dataclasses.replace(slot, ip_role=ip[-1]))  # a non-default choice
    custom = dataclasses.replace(old, slots=tuple(slots), mentality="positive")
    assert for_formation(custom, "4-4-2") == (custom, ())
    refitted, changed = for_formation(custom, "4-3-3")
    assert refitted.ip_formation == "4-3-3" and refitted.mentality == "positive"
    assert validate(refitted) == []
    old_positions = [catalogue["4-4-2"].slots[s.slot].position for s in custom.slots]
    for slot in refitted.slots:
        position = catalogue["4-3-3"].slots[slot.slot].position
        if position in old_positions:
            old_positions.remove(position)
            assert slot.slot not in changed
            assert slot.ip_role == [r.id for r in valid_roles(position, "ip")][-1]
        else:
            assert slot.slot in changed
            assert slot == default_tactic("4-3-3").slots[slot.slot]
    assert changed  # 4-4-2 and 4-3-3 differ in midfield and attack
