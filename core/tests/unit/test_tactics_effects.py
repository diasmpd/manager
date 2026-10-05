"""Tactics as quick-sim levers (spec 006 FR-005, SC-002)."""

import dataclasses

import pytest

from manager_core.domain.formation import load_catalogue
from manager_core.tactics.catalogue import OptionDef, load_options, valid_roles
from manager_core.tactics.effects import (
    GOOD_DOWN,
    GOOD_UP,
    NAMES,
    NEUTRAL,
    levers,
    option_effect,
)
from manager_core.tactics.model import Tactic, default_tactic


def _with(tactic: Tactic, **settings: str) -> Tactic:
    team = dict(tactic.team)
    team.update(settings)
    return dataclasses.replace(tactic, team=tuple(sorted(team.items())))


def test_neutral_against_neutral_is_neutral() -> None:
    base = default_tactic("4-4-2")
    assert levers(base, base) == NEUTRAL


def _moves(changes: dict[str, float]) -> tuple[bool, bool]:
    good = bad = False
    for name, value in changes.items():
        delta = value if name == "possession" else value - 1
        if delta == 0:
            continue
        if (name in GOOD_UP) == (delta > 0):
            good = True
        else:
            bad = True
    return good, bad


_OPTIONS = load_options()
_CASES = ([("team", o) for o in _OPTIONS.team if o.id != "progress_through"]
          + [("player", o) for o in _OPTIONS.player] + [("setup", o) for o in _OPTIONS.setups])


@pytest.mark.parametrize(("section", "option"), _CASES, ids=lambda c: getattr(c, "id", c))
def test_every_setting_has_an_effect_and_a_cost(section: str, option: OptionDef) -> None:
    for setting in option.settings:
        effect = option_effect(option.id, setting, section)
        if setting == option.default:
            assert effect == {}
            continue
        good, bad = _moves(effect)
        assert good and bad, (section, option.id, setting)


def test_role_only_stacking_stays_inside_one_option_budget() -> None:
    """Research R3: roles act mainly through suitability; their levers count per player, so the
    best role for a lever in every slot moves it by less than one option may (±15%)."""
    base = default_tactic("4-3-3")
    formation = load_catalogue()["4-3-3"]
    for lever in NAMES:
        sign = 1 if lever in GOOD_UP else -1
        slots = []
        for slot in base.slots:
            position = formation.slots[slot.slot].position
            best = {}
            for phase in ("ip", "oop"):
                options = valid_roles(position, phase)
                best[phase] = max(options, key=lambda r: sign * (
                    r.levers.get(lever, 0.0 if lever == "possession" else 1.0)))
            slots.append(dataclasses.replace(slot, ip_role=best["ip"].id,
                                             oop_role=best["oop"].id))
        value = getattr(levers(dataclasses.replace(base, slots=tuple(slots))), lever)
        if lever == "possession":
            assert abs(value) <= 3.0, lever
        else:
            assert 0.85 <= value <= 1.15, (lever, value)


def test_lever_names_are_classified() -> None:
    assert GOOD_UP.isdisjoint(GOOD_DOWN)
    assert {f.name for f in dataclasses.fields(NEUTRAL)} == GOOD_UP | GOOD_DOWN


def test_mentality_is_monotonic() -> None:
    base = default_tactic("4-4-2")
    previous = None
    for mentality in load_options().mentality.settings:
        lv = levers(dataclasses.replace(base, mentality=mentality))
        if previous is not None:
            assert lv.shot_rate > previous.shot_rate
            assert lv.allow_rate > previous.allow_rate
        previous = lv


def test_interactions_fire() -> None:
    base = default_tactic("4-4-2")
    high_line = _with(base, defensive_line="much_higher")
    counter = _with(base, attacking_transition="counter")
    assert levers(high_line, counter).allow_quality > levers(high_line, base).allow_quality
    press = _with(base, line_of_engagement="high_press")
    direct = _with(base, passing_directness="much_more_direct")
    assert levers(press, direct).allow_rate > levers(press, base).allow_rate


def test_progress_through_follows_the_weaker_flank() -> None:
    left = _with(default_tactic("4-4-2"), progress_through="left")
    assert levers(left, flank_balance=1.0).chance_quality > levers(left).chance_quality
    assert levers(left, flank_balance=-1.0).chance_quality < levers(left).chance_quality


def test_player_instructions_count_per_player() -> None:
    base = default_tactic("4-4-2")
    slots = list(base.slots)
    slots[10] = dataclasses.replace(slots[10], instructions=(("shoot", "more_often"),))
    one = levers(dataclasses.replace(base, slots=tuple(slots)))
    assert 1.0 < one.shot_rate < 1.01  # one player of eleven
