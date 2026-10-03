"""Result and match report codecs round-trip exactly (research R3)."""

import json
import random
from itertools import permutations
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career.codec import decode_result, encode_result
from manager_core.competition.results import MatchContext, PlaceholderProvider, Result
from manager_core.quicksim.engine import simulate_match
from manager_core.quicksim.provider import QuickSimProvider

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def provider() -> QuickSimProvider:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return QuickSimProvider(loaded.dataset)


def _round_trip(result: Result) -> Result:
    text = json.dumps(encode_result(result), sort_keys=True)  # must be plain JSON
    return decode_result(json.loads(text))


def test_quick_sim_results_round_trip(provider: QuickSimProvider) -> None:
    clubs = sorted(provider.dataset.clubs)
    for n, (home, away) in enumerate(list(permutations(clubs, 2))[:300]):
        result, _ = simulate_match(provider.team_sheet(home), provider.team_sheet(away),
                                   provider.dataset.players, provider.params,
                                   random.Random(f"codec:{n}"))
        assert _round_trip(result) == result


def test_results_with_shootouts_round_trip(provider: QuickSimProvider) -> None:
    dataset = provider.dataset
    for n in range(20):
        result, _ = simulate_match(provider.team_sheet("alvorada"),
                                   provider.team_sheet("serra-negra"), dataset.players,
                                   provider.params, random.Random(f"so:{n}"))
        shootout = provider.shootout("m", dataset.club("alvorada"), dataset.club("serra-negra"),
                                     MatchContext(1, "final"), random.Random(n),
                                     last_result=result)
        with_shootout = Result(result.home_goals, result.away_goals, result.source,
                               result.home_red, result.away_red, result.home_yellow,
                               result.away_yellow, shootout, result.report)
        assert _round_trip(with_shootout) == with_shootout


def test_placeholder_results_round_trip(provider: QuickSimProvider) -> None:
    placeholder = PlaceholderProvider(provider.dataset)
    result = placeholder.play("m", provider.dataset.club("alvorada"),
                              provider.dataset.club("serra-negra"), MatchContext(1, "x"),
                              random.Random(3))
    assert result.report is None and _round_trip(result) == result


def test_missing_field_fails_loudly() -> None:
    data = encode_result(Result(1, 0, "placeholder"))
    del data["home_goals"]
    with pytest.raises(KeyError):
        decode_result(data)
