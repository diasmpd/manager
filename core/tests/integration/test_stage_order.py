"""Regression: knockout stages are created in dependency order, not declaration order.

An `overall_places` entrant rule with `exclude_tracks` reads the entrants of the excluded track.
If the side-track stage was declared before the main-track stage drawing from the same source,
those entrants did not exist yet and nothing was excluded, so a club could play both tracks.
"""

from datetime import date
from pathlib import Path

import pytest

from manager_core import api
from manager_core.competition.rules import load_ruleset_file
from manager_core.competition.season import Season
from manager_core.domain.dataset import Dataset

ROOT = Path(__file__).resolve().parents[2]
BUNDLED = ROOT / "src" / "manager_core" / "reference" / "competitions" / "mg-modulo-i-2026.toml"


def _reordered(tmp_path: Path) -> Path:
    """The Mineiro ruleset with the Inconfidência semifinal declared before the semifinal and
    no `dates_with` tying it to the semifinal's dates."""
    text = BUNDLED.read_text("utf-8")
    head, *blocks = text.split("[[stages]]")
    by_id = {b.split('id = "', 1)[1].split('"', 1)[0]: b for b in blocks}
    side = by_id["inconfidencia-semifinal"].replace('dates_with = "semifinal"',
                                                    "may_exceed_window = true")
    order = ["primeira-fase", "inconfidencia-semifinal", "semifinal", "final",
             "inconfidencia-final"]
    body = "".join("[[stages]]" + (side if sid == "inconfidencia-semifinal" else by_id[sid])
                   for sid in order)
    path = tmp_path / "reordered.toml"
    path.write_text(head + body, "utf-8")
    return path


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(ROOT.parent / "data" / "sample")
    assert loaded.dataset is not None
    return loaded.dataset


def test_reordered_ruleset_never_puts_a_club_in_both_tracks(world: Dataset,
                                                            tmp_path: Path) -> None:
    ruleset = load_ruleset_file(_reordered(tmp_path))
    assert [s.id for s in ruleset.stages][1] == "inconfidencia-semifinal"
    for seed in range(60):
        season = Season.start(world, ruleset, 2026, seed)
        season.advance_to(date(2026, 12, 31))
        main = set(season.stage_entrants["semifinal"])
        side = set(season.stage_entrants["inconfidencia-semifinal"])
        assert len(main) == 4 and len(side) == 4, seed
        assert not main & side, (seed, sorted(main & side))
        # the side track is still the first four non-semifinalists from 5th place on
        eligible = [c for c in season.overall[4:] if c not in main]
        assert sorted(side) == sorted(eligible[:4]), seed
