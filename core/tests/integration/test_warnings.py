"""Warnings load the dataset but are listed for human review (FR-020)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import FlagKind, RecordType
from manager_core.ratings.ability import current_ability

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
WARNINGS = sorted(p for p in (FIXTURES / "warnings").iterdir() if p.is_dir())


@pytest.mark.parametrize("folder", WARNINGS, ids=lambda p: p.name)
def test_warning_fixture_loads_and_reports(folder: Path) -> None:
    code, file, record_id, field = (folder / "expected.txt").read_text("utf-8").strip().split(";")
    result = api.load_dataset(folder)
    assert result.dataset is not None, [i.code for i in result.report.errors]
    assert any(
        i.code == code and i.file == file and (i.record_id or "") == record_id
        and (i.field or "") == field
        for i in result.report.warnings
    ), [(i.code, i.file, i.record_id, i.field) for i in result.report.warnings]


def test_potential_raised_to_current_ability() -> None:
    result = api.load_dataset(FIXTURES / "valid" / "minimal")
    dataset = result.dataset
    assert dataset is not None
    player = dataset.player("p-a12")
    assert player.potential_ability == current_ability(player)
    flags = {f.flag for f in dataset.flags_for(RecordType.PLAYER, "p-a12")}
    assert FlagKind.POTENTIAL_RAISED in flags
    assert [i.code for i in result.report.warnings] == ["W010"]


def test_hidden_defaults_flagged() -> None:
    dataset = api.load_dataset(FIXTURES / "valid" / "minimal").dataset
    assert dataset is not None
    player = dataset.player("p-b12")
    assert (player.attributes.dirtiness, player.attributes.controversy) == (8, 6)
    flags = {f.flag for f in dataset.flags_for(RecordType.PLAYER, "p-b12")}
    assert FlagKind.HIDDEN_DEFAULTED in flags


def test_minimal_has_a_free_agent() -> None:
    dataset = api.load_dataset(FIXTURES / "valid" / "minimal").dataset
    assert dataset is not None
    assert [p.id for p in dataset.free_agents()] == ["p-fa01"]
