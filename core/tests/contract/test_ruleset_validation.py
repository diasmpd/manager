"""Contract: broken rulesets are rejected with their R-code and location (SC-006)."""

from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.rules import RulesetError, load_ruleset_file

RULESETS = Path(__file__).resolve().parents[1] / "fixtures" / "rulesets"
FIXTURES = sorted(RULESETS.glob("*.toml"))



def test_one_fixture_per_code() -> None:
    codes = {f.name[:4] for f in FIXTURES if f.name.startswith("R")}
    assert codes == {f"R{n:03d}" for n in range(1, 15)}


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.stem)
def test_fixture_rejected_with_code_and_location(fixture: Path) -> None:
    report = api.validate_ruleset(fixture)
    assert not report.ok
    expected = fixture.with_suffix(".expected.txt").read_text("utf-8").splitlines()
    if expected == ["R001"]:  # the location of an unreadable file is the file itself
        assert [(i.code, i.path) for i in report.issues] == [("R001", str(fixture))]
    else:
        assert [f"{i.code} {i.path}" for i in report.issues] == expected
    assert all(i.message for i in report.issues)


def test_three_defects_are_all_reported() -> None:
    report = api.validate_ruleset(RULESETS / "multi_three_defects.toml")
    assert sorted(i.code for i in report.issues) == ["R004", "R008", "R013"]


def test_loading_a_broken_file_raises_with_the_report() -> None:
    with pytest.raises(RulesetError) as info:
        load_ruleset_file(RULESETS / "R009_no_draw_last.toml")
    assert [i.code for i in info.value.report.issues] == ["R009"]


def test_missing_file_is_r001(tmp_path: Path) -> None:
    report = api.validate_ruleset(tmp_path / "nope.toml")
    assert [i.code for i in report.issues] == ["R001"]


def test_bundled_rulesets_validate_clean() -> None:
    summaries = api.list_rulesets()
    assert [s.id for s in summaries] == ["mg-modulo-i-2026", "test-liga-unica"]
    for s in summaries:
        assert api.load_ruleset(s.id).id == s.id


def test_disjoint_overall_places_do_not_overlap(tmp_path: Path) -> None:
    text = (RULESETS / "R012_tracks_overlap.toml").read_text("utf-8")
    fixed = tmp_path / "disjoint.toml"
    fixed.write_text(text.replace("places = [2, 3]", "places = [3, 4]"), "utf-8")
    assert api.validate_ruleset(fixed).ok


def test_exclude_tracks_clears_the_overlap(tmp_path: Path) -> None:
    text = (RULESETS / "R012_tracks_overlap.toml").read_text("utf-8")
    fixed = tmp_path / "excluded.toml"
    excluded = 'places = [2, 3], exclude_tracks = ["main"] }'
    fixed.write_text(text.replace("places = [2, 3] }", excluded), "utf-8")
    assert api.validate_ruleset(fixed).ok
