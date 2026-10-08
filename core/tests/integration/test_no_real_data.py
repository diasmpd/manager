"""SC-006: the public repository holds no real club or player data (spec 011, Constitution VI)."""

from pathlib import Path

from manager_core.realdata.guard import violations

REPO = Path(__file__).resolve().parents[3]


def test_no_real_data_is_tracked() -> None:
    assert violations(REPO) == []


def test_the_guard_catches_private_layouts(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / "cache" / "ogol").mkdir(parents=True)
    (tmp_path / "cache" / "ogol" / "x.html.gz").write_bytes(b"")
    (tmp_path / "corrections.csv").write_text("a\n", "utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "dataset.csv").write_text("format_version;fictional\n1;false\n", "utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    found = violations(tmp_path)
    assert any("cache/" in f for f in found)
    assert any("corrections.csv" in f for f in found)
    assert any("not declared fictional" in f for f in found)
