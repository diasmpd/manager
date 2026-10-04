"""AI clubs' styles and adaptation (spec 006 US4, FR-009, research R5)."""

import random
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.formation import load_catalogue
from manager_core.quicksim.engine import HOME, _Match
from manager_core.quicksim.report import Minute
from manager_core.quicksim.provider import QuickSimProvider
from manager_core.tactics import ai
from manager_core.tactics.catalogue import load_options
from manager_core.tactics.model import default_tactic, validate

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
MENTALITY = load_options().mentality.settings


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def test_styles_are_varied_and_deterministic(provider: QuickSimProvider) -> None:
    styles = provider.styles()
    assert set(styles) == set(provider.dataset.clubs)
    assert len(set(styles.values())) >= 3
    again = QuickSimProvider(provider.dataset).styles()
    assert again == styles


@pytest.mark.parametrize("style", ai.style_ids())
def test_every_style_is_a_valid_tactic_in_every_formation(style: str) -> None:
    for formation in load_catalogue():
        tactic = ai.style_tactic(style, formation)
        assert validate(tactic) == [], (style, formation)
        assert tactic.style == style


def test_a_big_underdog_away_sits_deeper() -> None:
    press = ai.style_tactic("high_press", "4-4-2")
    adapted = ai.pre_match(press, own=8.0, opponent=14.0, home=False)
    assert MENTALITY.index(adapted.mentality) <= MENTALITY.index("cautious")
    assert adapted.setting("line_of_engagement") == "mid_block"
    low = ai.style_tactic("low_block", "4-4-2")
    assert ai.pre_match(low, own=8.0, opponent=14.0, home=False).setting(
        "line_of_engagement") == "low_block"  # never pushed higher
    # at home, or with a small gap, nothing changes
    assert ai.pre_match(press, own=8.0, opponent=14.0, home=True) == press
    assert ai.pre_match(press, own=13.0, opponent=14.0, home=False) == press


def test_a_big_favourite_at_home_goes_one_step_up() -> None:
    balanced = ai.style_tactic("balanced", "4-4-2")
    assert ai.pre_match(balanced, own=14.0, opponent=8.0, home=True).mentality == "positive"
    assert ai.pre_match(balanced, own=14.0, opponent=8.0, home=False) == balanced


@pytest.mark.parametrize(("minute", "diff", "expected"), [
    (70, -1, "balanced"),  # not yet
    (71, -1, "positive"),
    (80, -2, "attacking"),
    (80, -3, "attacking"),
    (80, 0, "balanced"),
    (80, 1, "balanced"),
    (80, 2, "cautious"),
])
def test_in_match_steps_after_minute_70(minute: int, diff: int, expected: str) -> None:
    assert ai.in_match_mentality("balanced", minute, diff) == expected


def test_in_match_steps_stay_on_the_scale() -> None:
    assert ai.in_match_mentality("very_attacking", 85, -1) == "very_attacking"
    assert ai.in_match_mentality("very_defensive", 85, 3) == "very_defensive"


def test_the_engine_adapts_ai_sides_only(provider: QuickSimProvider) -> None:
    home, away = provider.team_sheet("ferroviario"), provider.team_sheet("mineracao")
    styled = ai.style_tactic("balanced", home.formation.name)
    user = default_tactic(away.formation.name)
    match = _Match(home, away, provider.dataset.players, provider.params, random.Random(1),
                   False, styled, user)
    before = match.sides[HOME].lv
    match.sides["away"].goals = 1  # the AI side trails
    match._adapt(75)
    assert match.sides[HOME].tactic is not None
    assert match.sides[HOME].tactic.mentality == "positive"
    assert match.sides[HOME].lv.shot_rate > before.shot_rate
    match.sides[HOME].goals = 3  # now the user's side trails by 2: it keeps its mentality
    match._adapt(80)
    assert match.sides["away"].tactic is not None
    assert match.sides["away"].tactic.mentality == "balanced"


def test_the_provider_uses_styles_and_the_users_tactic(provider: QuickSimProvider) -> None:
    home, away = provider.team_sheet("ferroviario"), provider.team_sheet("mineracao")
    h, a = provider.tactics_for(home, away)
    assert h is not None and h.style == provider.styles()["ferroviario"]
    assert a is not None and a.style == provider.styles()["mineracao"]
    mine = default_tactic(home.formation.name)
    provider.set_tactic("ferroviario", mine)
    try:
        assert provider.tactics_for(home, away)[0] == mine
    finally:
        provider.set_tactic("ferroviario", None)
    plain = QuickSimProvider(provider.dataset, ai_styles=False)
    assert plain.tactics_for(home, away) == (None, None)


def test_no_venue_adaptation_at_a_neutral_ground(provider: QuickSimProvider) -> None:
    press = ai.style_tactic("high_press", "4-4-2")
    assert ai.pre_match(press, own=8.0, opponent=14.0, home=False, neutral=True) == press
    assert ai.pre_match(press, own=14.0, opponent=8.0, home=True, neutral=True) == press
    strong, weak = provider.team_sheet("serra-negra"), provider.team_sheet("campo-florido")
    h, a = provider.tactics_for(strong, weak, neutral=True)
    styles = provider.styles()
    assert h == ai.style_tactic(styles["serra-negra"], strong.formation.name)
    assert a == ai.style_tactic(styles["campo-florido"], weak.formation.name)


def test_possession_follows_red_cards(provider: QuickSimProvider) -> None:
    home, away = provider.team_sheet("ferroviario"), provider.team_sheet("mineracao")
    match = _Match(home, away, provider.dataset.players, provider.params, random.Random(2),
                   False)
    before = match.home_possession
    side = match.sides[HOME]
    for _ in range(2):
        pid = next(pid for i, pid in sorted(side.on.items()) if i != 0)
        match._send_off(HOME, Minute(30), pid, "red")
    assert match.home_possession < before
