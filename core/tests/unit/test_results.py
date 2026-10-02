"""Result / Shootout invariants and the ResultProvider protocol."""

import pytest

from manager_core.competition.results import (
    PlaceholderProvider,
    Result,
    ResultProvider,
    Shootout,
)


def test_result_requires_non_negative_goals_and_source() -> None:
    assert Result(2, 1, "placeholder").home_goals == 2
    with pytest.raises(ValueError):
        Result(-1, 0, "placeholder")
    with pytest.raises(ValueError):
        Result(0, 0, "")


def test_shootout_winner_must_match_kicks() -> None:
    kicks = (("a", True), ("b", True), ("a", True), ("b", False), ("a", True), ("b", True),
             ("a", False), ("b", True), ("a", True), ("b", True))  # 4-4 after 5 each
    with pytest.raises(ValueError):
        Shootout(kicks, winner_id="a")
    sudden = (*kicks, ("a", True), ("b", False))
    assert Shootout(sudden, winner_id="a").score == {"a": 5, "b": 4}


def test_shootout_cannot_end_early_without_being_decided() -> None:
    with pytest.raises(ValueError):
        Shootout((("a", True), ("b", False)), winner_id="a")


def test_shootout_can_end_early_when_decided() -> None:
    kicks = (("a", True), ("b", False), ("a", True), ("b", False), ("a", True), ("b", False))
    assert Shootout(kicks, winner_id="a").score == {"a": 3, "b": 0}


def test_placeholder_satisfies_protocol() -> None:
    assert isinstance(PlaceholderProvider.__new__(PlaceholderProvider), ResultProvider)
