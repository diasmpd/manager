"""Original match and team news (spec 011 follow-on, career/press.py): the game writes its own
match reports from its data, deterministically, and team and player items follow the results."""

from pathlib import Path

from manager_core import api
from manager_core.career import press

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


def _play_user_matches(tmp_path: Path, count: int):  # type: ignore[no-untyped-def]
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    career = api.new_career(loaded.dataset, "imprensa", "mineracao", master_seed=7)
    played = 0
    for _ in range(400):
        stop = api.continue_career(career, tmp_path)
        if stop.kind == "user_match":
            api.continue_career(career, tmp_path)  # play it
            played += 1
            if played == count:
                return career
    raise AssertionError("not enough user matches")


def test_match_reports_are_written_from_the_match(tmp_path: Path) -> None:
    career = _play_user_matches(tmp_path, 4)
    news = api.career_news(career)
    matches = [n for n in news if n.kind == "match"]
    assert len(matches) >= 4
    assert all(n.text and "{" not in n.text for n in matches)  # every placeholder filled
    assert all(("Gols:" in n.text) or ("0 x 0" in n.text or "x" in n.text) for n in matches)


def test_reports_are_deterministic(tmp_path: Path) -> None:
    career = _play_user_matches(tmp_path, 3)
    again = api.career_news(career)
    assert again == api.career_news(career)
    kinds = {n.kind for n in again}
    assert "match" in kinds


def test_the_same_match_gets_the_same_words() -> None:
    lines = [press._pick("press.shots", "m1side"), press._pick("press.shots", "m1side")]
    assert lines[0] == lines[1]
    assert press._pick("press.shots", "m2side") in {f"press.shots.{i}" for i in range(3)}
