"""Owner corrections (spec 011 R5, T019-T021), on a copy of the fictional sample dataset."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import FlagKind
from manager_core.realdata import corrections
from manager_core.realdata.__main__ import main
from manager_core.realdata.corrections import Correction

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"
KEEPER = "p-000001"  # finishing 3, height 191


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    out = tmp_path / "dataset"
    shutil.copytree(SAMPLE, out)
    return out


def _fix(field: str, old: str, new: str, record: str = KEEPER, kind: str = "player",
         note: str = "") -> Correction:
    return Correction(kind, record, field, old, new, "2026-10-19", note)


def test_corrections_apply_last_and_flag_the_record(dataset: Path) -> None:
    applied = corrections.apply(dataset, [
        _fix("finishing", "3", "5"), _fix("height_cm", "191", "193"),
        _fix("color_primary", "#C8102E", "#B00020", record="alvorada", kind="club"),
        _fix("finishing", "5", "6"),  # a later row wins
    ])
    assert applied.applied == 4 and applied.notes == []
    loaded = api.load_dataset(dataset)
    assert loaded.report.ok and loaded.dataset is not None
    player = loaded.dataset.players[KEEPER]
    assert player.attributes.get("finishing") == 6 and player.height_cm == 193
    assert loaded.dataset.clubs["alvorada"].color_primary == "#B00020"
    flags = {(f.record_id, f.flag): f.detail for f in loaded.dataset.record_flags}
    assert flags[(KEEPER, FlagKind.MANUALLY_EDITED)] == "finishing, height_cm"
    assert (("alvorada", FlagKind.MANUALLY_EDITED)) in flags


def test_a_source_change_under_a_correction_is_kept_and_reported(dataset: Path) -> None:
    applied = corrections.apply(dataset, [_fix("finishing", "9", "12")])  # the source said 9
    assert applied.applied == 1
    assert "source changed under a correction" in applied.notes[0]
    assert corrections.current_value(dataset, "player", KEEPER, "finishing") == "12"


def test_a_gone_record_or_an_unknown_field_is_kept_and_reported(dataset: Path) -> None:
    applied = corrections.apply(dataset, [_fix("finishing", "3", "5", record="p-999999"),
                                          _fix("charisma", "1", "2")])
    assert applied.applied == 0
    assert "record is gone" in applied.notes[0] and "no such field" in applied.notes[1]


def test_the_file_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "corrections.csv"
    corrections.append(path, _fix("finishing", "3", "5", note="viu jogar; finaliza bem"))
    corrections.append(path, _fix("finishing", "5", "6"))
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert path.read_text("utf-8-sig").count("record_type;") == 1
    rows = corrections.read(path)
    assert [(r.old_value, r.new_value) for r in rows] == [("3", "5"), ("5", "6")]
    assert rows[0].note == "viu jogar; finaliza bem"


def test_the_correct_command(dataset: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    args = ["correct", "--data-repo", str(repo), "--out", str(dataset)]
    assert main([*args, "--record", f"player:{KEEPER}", "--field", "finishing",
                 "--value", "7", "--note", "olho do dono"]) == 0
    row = corrections.read(repo / "corrections.csv")[0]
    assert (row.old_value, row.new_value, row.note) == ("3", "7", "olho do dono")
    # refused: a value the game would reject, an unknown field, an unknown record
    assert main([*args, "--record", f"player:{KEEPER}", "--field", "finishing",
                 "--value", "25"]) == 1
    assert main([*args, "--record", f"player:{KEEPER}", "--field", "charisma",
                 "--value", "5"]) == 1
    assert main([*args, "--record", "player:p-999999", "--field", "finishing",
                 "--value", "5"]) == 1
    assert len(corrections.read(repo / "corrections.csv")) == 1
