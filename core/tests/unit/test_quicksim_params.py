"""Quick-sim model parameters as data (research R9)."""

from pathlib import Path

import pytest

from manager_core.quicksim.params import (
    ModelParamsError,
    dump_params,
    load_params,
    load_params_file,
)


def test_bundled_parameters_load() -> None:
    params = load_params()
    assert params.model_version
    assert 0 < params.rates.shot < 1
    assert params.stoppage.first[0] <= params.stoppage.first[1]
    assert params.scorers.line_weights.goalkeeper == 0.0


def test_hash_is_stable_and_value_sensitive() -> None:
    params = load_params()
    assert params.params_hash == load_params().params_hash
    changed = params.with_values(**{"rates.shot": params.rates.shot + 0.001})
    assert changed.params_hash != params.params_hash
    assert changed.rates.shot == pytest.approx(params.rates.shot + 0.001)


def test_dump_round_trips(tmp_path: Path) -> None:
    params = load_params()
    path = tmp_path / "model.toml"
    path.write_text(dump_params(params), "utf-8")
    assert load_params_file(path) == params


def _broken(tmp_path: Path, old: str, new: str) -> Path:
    text = dump_params(load_params())
    assert old in text, old
    path = tmp_path / "broken.toml"
    path.write_text(text.replace(old, new, 1), "utf-8")
    return path


def test_missing_key_is_q001_with_path(tmp_path: Path) -> None:
    params = load_params()
    path = _broken(tmp_path, f"foul = {params.rates.foul!r}\n", "")
    with pytest.raises(ModelParamsError) as info:
        load_params_file(path)
    assert ("Q001", "rates.foul") in info.value.problems


def test_rate_outside_unit_interval_is_rejected(tmp_path: Path) -> None:
    params = load_params()
    path = _broken(tmp_path, f"shot = {params.rates.shot!r}", "shot = 1.5")
    with pytest.raises(ModelParamsError) as info:
        load_params_file(path)
    assert ("Q001", "rates.shot") in info.value.problems


def test_ranges_must_be_ordered(tmp_path: Path) -> None:
    params = load_params()
    lo, hi = params.stoppage.first
    path = _broken(tmp_path, f"first = [{lo}, {hi}]", f"first = [{hi + 1}, {lo}]")
    with pytest.raises(ModelParamsError) as info:
        load_params_file(path)
    assert ("Q001", "stoppage.first") in info.value.problems
