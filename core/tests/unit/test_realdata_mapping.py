"""Source vocabulary -> game values (spec 011): positions, nations and feet."""

from manager_core.domain.positions import Position
from manager_core.realdata.mapping import familiarity, feet, nations, positions_from_label


def test_ogol_labels_run_together_split_longest_first() -> None:
    assert positions_from_label("Goleiro") == [Position.GK]
    assert positions_from_label("Ponta Direita Meia Ofensivo") == [Position.AMR, Position.AMC]
    assert positions_from_label("Meia Central Volante") == [Position.MC, Position.DM]
    assert positions_from_label("Meia") == [Position.MC]
    assert positions_from_label("2º Atacante Ponta Esquerda") == [Position.ST, Position.AML]
    assert positions_from_label("Centroavante Atacante") == [Position.ST]  # no repeats
    assert positions_from_label("Líbero Zagueiro") == [Position.DC]  # unknown words skipped
    assert positions_from_label(None) == []


def test_the_first_position_is_natural_and_full_backs_get_their_wing_back() -> None:
    assert familiarity([Position.DL, Position.DC]) == {
        Position.DL: 20, Position.DC: 16, Position.WBL: 14}
    assert familiarity([Position.ST]) == {Position.ST: 20}


def test_nations_single_dual_and_unknown() -> None:
    assert nations("Brasil") == (("BRA",), [])
    assert nations("Brasil Itália") == (("BRA", "ITA"), [])
    assert nations("Brasil / Portugal") == (("BRA", "POR"), [])
    assert nations("Irlanda do Norte") == (("NIR",), [])  # not Irlanda + "do Norte"
    assert nations("Portugal São Tomé e Príncipe") == (("POR", "STP"), [])
    assert nations("Atlântida Brasil") == (("BRA",), ["Atlântida"])
    assert nations(None) == ((), [])


def test_feet_are_fixed_per_player() -> None:
    left, right = feet("right", "p-og1")
    assert right == 20 and 5 <= left <= 12
    assert feet("right", "p-og1") == (left, right)
    assert feet("left", "p-og1") == (right, left)
    assert feet("both", "p-og1") == (18, 18)
    assert feet(None, "p-og1") == (left, right)  # unknown: right-footed, the common case
