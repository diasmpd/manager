"""The attribute-synthesis model (spec 011 R4), on fictional signals and the sample's players."""

import dataclasses
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.attributes import Attributes
from manager_core.domain.positions import Position
from manager_core.ratings.ability import best_position, current_ability
from manager_core.realdata import synthesis
from manager_core.realdata.synthesis import Signals, attributes_for, synthesise, target_ability

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def sample_players():  # type: ignore[no-untyped-def]
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset.players


@pytest.mark.parametrize("ca", [45, 80, 110, 140, 170])
def test_the_games_own_formula_lands_on_the_target(sample_players, ca: int) -> None:  # type: ignore[no-untyped-def]
    """Attributes generated for a target CA give that CA back through `current_ability`, at the
    player's natural position (so stars and team strength mean what the model meant)."""
    for player in list(sample_players.values())[:40]:
        position = best_position(player)
        attrs = attributes_for(position, ca, 27, player.id)
        rebuilt = dataclasses.replace(player, attributes=Attributes(**attrs))
        assert abs(current_ability(rebuilt) - ca) <= 2, (player.id, position)
        assert all(1 <= v <= 20 for v in attrs.values())


def test_position_profiles() -> None:
    keeper = attributes_for(Position.GK, 120, 27, "k")
    winger = attributes_for(Position.AML, 120, 27, "w")
    centre_back = attributes_for(Position.DC, 120, 27, "c")
    assert keeper["reflexes"] > keeper["finishing"] + 5
    assert winger["crossing"] > winger["reflexes"] + 5 and winger["pace"] >= winger["heading"]
    assert centre_back["marking"] > centre_back["crossing"]
    assert centre_back["heading"] > centre_back["dribbling"]


def test_age_curves() -> None:
    young = attributes_for(Position.MC, 110, 18, "same")
    old = attributes_for(Position.MC, 110, 35, "same")
    assert young["pace"] > old["pace"] and young["acceleration"] > old["acceleration"]
    assert old["decisions"] > young["decisions"] and old["composure"] > young["composure"]


def test_determinism_and_variety() -> None:
    a = synthesise(Signals("p-og1", Position.ST, "D", 26, 0.8, 200_000, 100_000, 0.4))
    assert a == synthesise(Signals("p-og1", Position.ST, "D", 26, 0.8, 200_000, 100_000, 0.4))
    b = synthesise(Signals("p-og2", Position.ST, "D", 26, 0.8, 200_000, 100_000, 0.4))
    assert a.attributes != b.attributes and abs(a.current_ability - b.current_ability) <= 1


def test_signals_move_ability_the_right_way() -> None:
    base = Signals("p", Position.MC, "D", 27)
    serie_a = target_ability(dataclasses.replace(base, division="A"))[0]
    state_only = target_ability(dataclasses.replace(base, division="none"))[0]
    assert serie_a > target_ability(base)[0] > state_only
    starter = target_ability(dataclasses.replace(base, games_share=1.0))[0]
    unused = target_ability(dataclasses.replace(base, games_share=0.0))[0]
    assert starter > unused
    valued = target_ability(dataclasses.replace(base, value_eur=1_000_000,
                                                club_median_value_eur=100_000))[0]
    assert valued > target_ability(base)[0]
    assert target_ability(dataclasses.replace(base, age=19))[0] < target_ability(base)[0]
    assert target_ability(dataclasses.replace(base, age=36))[0] < target_ability(base)[0]


def test_confidence_says_what_was_known() -> None:
    assert target_ability(Signals("p", Position.MC, "D", 27, 0.7, 50_000, 40_000))[1] == "high"
    assert target_ability(Signals("p", Position.MC, "D", 27, 0.7))[1] == "medium"
    assert target_ability(Signals("p", Position.MC, "D", 27))[1] == "low"


def test_no_other_games_ratings_are_inputs() -> None:
    """Owner decision 1 (2026-10-07): ability is ours. The signals carry no rating field."""
    names = {f.name for f in dataclasses.fields(Signals)}
    assert not names & {"rating", "overall", "fm_ca", "fifa", "sofifa", "brasileirinho"}
    assert synthesis.params()["model_version"].startswith("synthesis")
