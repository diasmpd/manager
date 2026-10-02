"""FR-022: format versioning. (The "older supported version" case is first testable when spec
011 introduces v1.1.)"""

from collections.abc import Callable
from pathlib import Path

import pytest

from manager_core import api
from manager_core.io.dialect import read_table, write_table

MINIMAL = Path(__file__).resolve().parents[1] / "fixtures" / "valid" / "minimal"


def _with_version(tmp_dataset: Callable[[Path], Path], version: str) -> Path:
    folder = tmp_dataset(MINIMAL)
    table = read_table(folder / "dataset.csv")
    row = dict(table.rows[0].values, format_version=version)
    write_table(folder / "dataset.csv", list(table.columns), [[row[c] for c in table.columns]])
    return folder


def test_current_version_accepted(tmp_dataset: Callable[[Path], Path]) -> None:
    assert api.load_dataset(_with_version(tmp_dataset, "1.0")).dataset is not None


def test_newer_major_refused_clearly(tmp_dataset: Callable[[Path], Path]) -> None:
    report = api.validate_dataset(_with_version(tmp_dataset, "2.0"))
    issue = next(i for i in report.errors if i.code == "E031")
    assert "2.0" in issue.message and "Atualize" in issue.message


@pytest.mark.parametrize("version", ["abc", "1", "0.9", ""])
def test_garbage_or_unsupported_version(tmp_dataset: Callable[[Path], Path], version: str) -> None:
    report = api.validate_dataset(_with_version(tmp_dataset, version))
    assert {i.code for i in report.errors} & {"E030", "E005"}
