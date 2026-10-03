"""Numerical (dis)advantage after red cards follows the numbers on the pitch, as in real
football: 10 v 11 favours the eleven, 10 v 10 is even again."""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.positions import Position
from manager_core.quicksim.engine import _Match
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.quicksim.report import AWAY, HOME, Minute

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def _match(provider: QuickSimProvider) -> _Match:
    return _Match(provider.team_sheet("mineracao"), provider.team_sheet("rio-turvo"),
                  provider.dataset.players, provider.params, random.Random(1), neutral=False)


def _send_off_outfielder(match: _Match, side: str) -> None:
    s = match.sides[side]
    pid = next(pid for i, pid in s.on_pitch() if s.sheet.slot_position(i) is Position.DC)
    match._send_off(side, Minute(20), pid, "red")


def test_ten_against_eleven(provider: QuickSimProvider) -> None:
    match = _match(provider)
    params = provider.params.state
    eleven = match._state(HOME, 30)[0]
    _send_off_outfielder(match, HOME)
    assert match._state(HOME, 30)[0] == pytest.approx(eleven * (1 - params.short_handed))
    assert match._state(AWAY, 30)[0] == pytest.approx(eleven * (1 + params.man_up))


def test_ten_against_ten_is_even(provider: QuickSimProvider) -> None:
    match = _match(provider)
    eleven = match._state(HOME, 30)[0]
    _send_off_outfielder(match, HOME)
    _send_off_outfielder(match, AWAY)
    assert match._state(HOME, 30)[0] == pytest.approx(eleven)
    assert match._state(AWAY, 30)[0] == pytest.approx(eleven)


def test_nine_against_ten(provider: QuickSimProvider) -> None:
    match = _match(provider)
    params = provider.params.state
    eleven = match._state(HOME, 30)[0]
    _send_off_outfielder(match, HOME)
    _send_off_outfielder(match, HOME)
    _send_off_outfielder(match, AWAY)
    assert match._state(HOME, 30)[0] == pytest.approx(eleven * (1 - params.short_handed))
    assert match._state(AWAY, 30)[0] == pytest.approx(eleven * (1 + params.man_up))
