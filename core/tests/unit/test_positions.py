import pytest

from manager_core.domain.positions import (
    FamiliarityBand,
    Line,
    Position,
    PositionFamiliarity,
    band_for,
    familiarity_factor,
)


def test_fm_position_order() -> None:
    assert [p.value for p in Position] == [
        "GK", "DL", "DC", "DR", "WBL", "WBR", "DM", "ML", "MC", "MR", "AML", "AMC", "AMR", "ST",
    ]


@pytest.mark.parametrize(
    ("codes", "line"),
    [
        (["GK"], Line.GK),
        (["DL", "DC", "DR", "WBL", "WBR"], Line.DEF),
        (["DM", "ML", "MC", "MR"], Line.MID),
        (["AML", "AMC", "AMR", "ST"], Line.ATT),
    ],
)
def test_lines(codes: list[str], line: Line) -> None:
    assert all(Position(c).line is line for c in codes)


@pytest.mark.parametrize(
    ("value", "band"),
    [
        (20, FamiliarityBand.NATURAL), (18, FamiliarityBand.NATURAL),
        (17, FamiliarityBand.ACCOMPLISHED), (15, FamiliarityBand.ACCOMPLISHED),
        (14, FamiliarityBand.COMPETENT), (12, FamiliarityBand.COMPETENT),
        (11, FamiliarityBand.UNCONVINCING), (9, FamiliarityBand.UNCONVINCING),
        (8, FamiliarityBand.AWKWARD), (5, FamiliarityBand.AWKWARD),
        (4, FamiliarityBand.INEFFECTUAL), (1, FamiliarityBand.INEFFECTUAL),
    ],
)
def test_bands(value: int, band: FamiliarityBand) -> None:
    assert band_for(value) is band


@pytest.mark.parametrize(
    ("value", "factor"),
    [(20, 1.00), (18, 0.99), (15, 0.96), (12, 0.90), (9, 0.82), (5, 0.70), (1, 0.55)],
)
def test_factor_anchors(value: int, factor: float) -> None:
    assert familiarity_factor(value) == pytest.approx(factor)


def test_factor_interpolates_linearly() -> None:
    assert familiarity_factor(19) == pytest.approx(0.995)
    assert familiarity_factor(3) == pytest.approx(0.625)


def test_factor_is_monotonic() -> None:
    values = [familiarity_factor(v) for v in range(1, 21)]
    assert values == sorted(values)


@pytest.mark.parametrize("bad", [0, 21])
def test_factor_rejects_out_of_range(bad: int) -> None:
    with pytest.raises(ValueError):
        familiarity_factor(bad)


def test_familiarity_defaults_and_naturals() -> None:
    fam = PositionFamiliarity({Position.DC: 20, Position.DM: 15, Position.DR: 12})
    assert fam.get(Position.ST) == 1
    assert fam.natural_positions() == (Position.DC, Position.DM)  # FM order, >= 15


def test_familiarity_range() -> None:
    with pytest.raises(ValueError):
        PositionFamiliarity({Position.DC: 21})
