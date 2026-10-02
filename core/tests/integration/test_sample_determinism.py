"""SC-002: the generator is deterministic and the committed sample matches it byte for byte."""

from pathlib import Path

from manager_core import api


def _export(seed: int, out: Path) -> Path:
    api.export_dataset(api.generate_sample(seed), out)
    return out


def test_committed_sample_matches_generator(sample_dir: Path, tmp_path: Path) -> None:
    fresh = _export(api.DEFAULT_SEED, tmp_path / "fresh")
    committed = sorted(p.name for p in sample_dir.glob("*.csv"))
    assert committed == sorted(p.name for p in fresh.glob("*.csv"))
    for name in committed:
        assert (sample_dir / name).read_bytes() == (fresh / name).read_bytes(), name


def test_same_seed_same_output(tmp_path: Path) -> None:
    a = _export(7, tmp_path / "a")
    b = _export(7, tmp_path / "b")
    for f in a.glob("*.csv"):
        assert f.read_bytes() == (b / f.name).read_bytes(), f.name


def test_different_seed_differs(tmp_path: Path) -> None:
    a = _export(1, tmp_path / "a")
    b = _export(2, tmp_path / "b")
    assert (a / "attributes.csv").read_bytes() != (b / "attributes.csv").read_bytes()
