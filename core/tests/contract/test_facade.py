"""Contract: core facade (specs/001-core-domain-model/contracts/facade.md)."""

import inspect

from manager_core import api

EXPECTED = {
    "load_dataset": ["path"],
    "validate_dataset": ["path"],
    "export_dataset": ["dataset", "path"],
    "generate_sample": ["seed"],
    "list_clubs": ["dataset"],
    "squad": ["dataset", "club_id", "sort"],
    "player_profile": ["dataset", "player_id", "include_hidden"],
    "rank_for_position": ["dataset", "club_id", "position"],
    "suggest_lineup": ["dataset", "club_id", "formation"],
    "list_formations": [],
}


def test_facade_functions_and_parameters() -> None:
    for name, params in EXPECTED.items():
        fn = getattr(api, name)
        assert list(inspect.signature(fn).parameters) == params, name


def test_defaults() -> None:
    assert inspect.signature(api.generate_sample).parameters["seed"].default == 20261002
    assert inspect.signature(api.squad).parameters["sort"].default == "position"
    assert inspect.signature(api.player_profile).parameters["include_hidden"].default is False
    assert inspect.signature(api.suggest_lineup).parameters["formation"].default == "4-4-2"


def test_not_found_error() -> None:
    err = api.NotFoundError("club", "x")
    assert (err.kind, err.id) == ("club", "x")
