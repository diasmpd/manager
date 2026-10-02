from datetime import date
from pathlib import Path

import pytest

from manager_core.io.dialect import DialectError, format_value, read_table, write_table


def test_canonical_write(tmp_path: Path) -> None:
    path = tmp_path / "t.csv"
    rows = [["b", format_value(2)], ["a", format_value(date(2001, 5, 14))]]
    write_table(path, ["id", "value"], rows, key_columns=1)
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    assert b"\r\n" not in raw
    assert raw.decode("utf-8-sig") == "id;value\na;2001-05-14\nb;2\n"


def test_write_is_byte_stable(tmp_path: Path) -> None:
    rows = [["x", "Uberlândia"], ["a", "São João del-Rei"]]
    write_table(tmp_path / "1.csv", ["id", "city"], rows, key_columns=1)
    write_table(tmp_path / "2.csv", ["id", "city"], list(reversed(rows)), key_columns=1)
    assert (tmp_path / "1.csv").read_bytes() == (tmp_path / "2.csv").read_bytes()


def test_format_values() -> None:
    assert format_value(None) == ""
    assert format_value(True) == "true"
    assert format_value(False) == "false"
    assert format_value(15000000) == "15000000"
    assert format_value(("BRA", "ITA")) == "BRA|ITA"


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_canonical_read(tmp_path: Path, bom: bytes, newline: bytes) -> None:
    path = tmp_path / "t.csv"
    content = newline.join(["id;city".encode(), " a ; São João ".encode("utf-8"), b""])
    path.write_bytes(bom + content)
    table = read_table(path)
    assert table.columns == ("id", "city")
    assert len(table.rows) == 1
    row = table.rows[0]
    assert row.number == 2  # spreadsheet row number (header is row 1)
    assert row.values == {"id": "a", "city": "São João"}


def test_non_utf8_raises_e033(tmp_path: Path) -> None:
    path = tmp_path / "t.csv"
    path.write_bytes("id;city\na;São Paulo\n".encode("cp1252"))
    with pytest.raises(DialectError) as err:
        read_table(path)
    assert err.value.code == "E033"
