"""Contract: every active error code rejects its fixture with a precise location (SC-004)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.io.validate import Issue

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
INVALID = sorted(p for p in (FIXTURES / "invalid").iterdir() if p.is_dir())
ACTIVE_CODES = {
    "E001", "E002", "E003", "E004", "E005", "E010", "E011", "E013", "E014", "E016", "E017",
    "E018", "E019", "E020", "E021", "E022", "E023", "E024", "E025", "E030", "E031", "E032",
    "E033",
}


def _expected(folder: Path) -> list[tuple[str, str, str, str]]:
    lines = (folder / "expected.txt").read_text(encoding="utf-8").splitlines()
    return [tuple(line.split(";")) for line in lines if line]  # type: ignore[misc]


def _matches(issue: Issue, code: str, file: str, record_id: str, field: str) -> bool:
    return (
        issue.code == code
        and issue.file == file
        and (issue.record_id or "") == record_id
        and (issue.field or "") == field
    )


def test_every_active_code_has_a_fixture() -> None:
    covered = {folder.name[:4] for folder in INVALID if folder.name.startswith("E")}
    assert covered == ACTIVE_CODES
    assert len(covered) >= 15  # SC-004


@pytest.mark.parametrize("folder", INVALID, ids=lambda p: p.name)
def test_fixture_is_rejected_with_location(folder: Path) -> None:
    result = api.load_dataset(folder)
    assert result.dataset is None  # all-or-nothing: nothing constructed
    assert not result.report.ok
    for code, file, record_id, field in _expected(folder):
        assert any(_matches(i, code, file, record_id, field) for i in result.report.errors), (
            code, [(i.code, i.file, i.record_id, i.field) for i in result.report.errors]
        )


def test_all_independent_errors_reported_in_one_pass() -> None:
    report = api.validate_dataset(FIXTURES / "invalid" / "multi_3_defects")
    assert len(report.errors) == 3


def test_issues_are_ordered_by_file_row_field() -> None:
    report = api.validate_dataset(FIXTURES / "invalid" / "multi_3_defects")
    keys = [(i.file, i.row or 0, i.field or "") for i in report.issues]
    assert keys == sorted(keys)


def test_messages_are_portuguese() -> None:
    report = api.validate_dataset(FIXTURES / "invalid" / "E004_attribute_out_of_range")
    assert "intervalo 1–20" in report.errors[0].message
