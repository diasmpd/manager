"""pt-BR Excel tolerance (spec 011 R6, T022): a dataset opened and re-saved in Excel loads
unchanged. Reading only: writing stays canonical."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from manager_core import api
from manager_core.io.dialect import read_text_table
from manager_core.io.validate import parse_bool, parse_date

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _br_dates(text: str) -> str:
    return ISO.sub(lambda m: f"{m.group(3)}/{m.group(2)}/{m.group(1)}", text)


def _commas(text: str) -> str:
    """Excel's "CSV UTF-8" where the list separator is a comma: cells with commas quoted, and
    stray spaces around the id cells."""
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=",", lineterminator="\r\n")
    for row in rows:
        writer.writerow([f" {c} " if i == 0 and c else c for i, c in enumerate(row)])
    return buffer.getvalue()


def _resave(tmp_path: Path, change: Callable[[str], str], encoding: str) -> Path:
    """Every file of the sample, as Excel would write it back."""
    out = tmp_path / "resaved"
    out.mkdir()
    for path in SAMPLE.glob("*.csv"):
        text = path.read_bytes().decode("utf-8-sig")
        (out / path.name).write_bytes(change(text).encode(encoding))
    return out


@pytest.mark.parametrize(("label", "change", "encoding"), [
    # pt-BR Excel, "CSV (separado por vírgulas)": Windows-1252, no BOM, CRLF, dd/mm/yyyy,
    # VERDADEIRO/FALSO
    ("pt-BR plain CSV",
     lambda t: _br_dates(t).replace("true", "VERDADEIRO").replace("false", "FALSO")
     .replace("\n", "\r\n"), "cp1252"),
    # "CSV UTF-8" saved where the list separator is a comma, with stray spaces
    ("CSV UTF-8, commas", lambda t: _commas(t), "utf-8-sig"),
])
def test_a_resaved_dataset_loads_unchanged(tmp_path: Path, label: str,
                                           change: Callable[[str], str], encoding: str) -> None:
    original = api.load_dataset(SAMPLE).dataset
    resaved = api.load_dataset(_resave(tmp_path, change, encoding))
    assert resaved.report.ok, [i.message for i in resaved.report.errors]
    assert resaved.dataset == original, label


def test_the_typed_parsers_take_excel_forms() -> None:
    assert parse_date("01/03/1999") == parse_date("1999-03-01") == parse_date("1/3/1999")
    assert parse_bool("VERDADEIRO") and not parse_bool("FALSO") and parse_bool("true")
    with pytest.raises(ValueError):
        parse_date("31/02/2000")
    with pytest.raises(ValueError):
        parse_bool("sim")


def test_semicolon_stays_the_separator_when_both_appear() -> None:
    table = read_text_table("club_id;name\nalvorada;Grêmio, o Alvorada\n")
    assert table.rows[0].values["name"] == "Grêmio, o Alvorada"
