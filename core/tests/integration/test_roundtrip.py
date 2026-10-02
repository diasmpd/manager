"""SC-003 / FR-021: export -> import is lossless; exporting twice is byte-identical."""

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.club import ExternalRef
from manager_core.domain.dataset import Dataset

pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _roundtrip(dataset: Dataset, folder: Path) -> Dataset:
    api.export_dataset(dataset, folder)
    result = api.load_dataset(folder)
    assert result.dataset is not None, [i.code for i in result.report.errors]
    return result.dataset


@pytest.mark.parametrize("source", ["sample", "minimal"])
def test_lossless(source: str, sample_dir: Path, tmp_path: Path) -> None:
    folder = sample_dir if source == "sample" else FIXTURES / "valid" / "minimal"
    original = api.load_dataset(folder).dataset
    assert original is not None
    again = _roundtrip(original, tmp_path / "out")
    assert again == original
    assert again.record_flags == original.record_flags  # flags persist


def test_export_twice_byte_identical(sample_dir: Path, tmp_path: Path) -> None:
    dataset = api.load_dataset(sample_dir).dataset
    assert dataset is not None
    api.export_dataset(dataset, tmp_path / "a")
    api.export_dataset(dataset, tmp_path / "b")
    for f in (tmp_path / "a").glob("*.csv"):
        assert f.read_bytes() == (tmp_path / "b" / f.name).read_bytes(), f.name


def test_external_refs_survive(tmp_path: Path) -> None:
    original = api.load_dataset(FIXTURES / "valid" / "minimal").dataset
    assert original is not None
    club = dataclasses.replace(
        original.club("clube-a"), external_refs=(ExternalRef("transfermarkt", "12345"),)
    )
    player = dataclasses.replace(
        original.player("p-a03"), external_refs=(ExternalRef("sofifa", "999"),)
    )
    edited = dataclasses.replace(
        original,
        clubs={**original.clubs, "clube-a": club},
        players={**original.players, "p-a03": player},
    )
    again = _roundtrip(edited, tmp_path / "refs")
    assert again.club("clube-a").external_refs == club.external_refs
    assert again.player("p-a03").external_refs == player.external_refs


@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    notes=st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), max_size=40),
    names=st.lists(st.text(alphabet="ãáâçéêíóôõúü ABCdefXYZ-'", min_size=2, max_size=30)
                   .map(str.strip).filter(lambda s: len(s) >= 2), min_size=1, max_size=3),
    capacity=st.integers(500, 250_000),
    reference=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
def test_property_roundtrip(tmp_path: Path, notes: str, names: list[str], capacity: int,
                            reference: date) -> None:
    base = api.load_dataset(FIXTURES / "valid" / "minimal").dataset
    assert base is not None
    club = dataclasses.replace(base.club("clube-a"), name=names[0], stadium_capacity=capacity)
    dataset = dataclasses.replace(
        base, notes=notes.strip(), clubs={**base.clubs, "clube-a": club},
        reference_date=reference,
    )
    folder = tmp_path / f"p{abs(hash((notes, tuple(names), capacity, reference)))}"
    assert _roundtrip(dataset, folder) == dataset
