"""The 2D match view's data (spec 008b, contract 1.4): kits and numbers, the pitch description
of a live match, and the positions sent chunk by chunk, which add up to the stored record and
change nothing in the match."""

import base64
import struct
from itertools import permutations
from pathlib import Path
from typing import Any

import pytest

from manager_core import api
from manager_core.domain.dataset import Dataset
from manager_core.positional import view
from manager_core.positional.record import WIDTH

from .test_live_match import SAMPLE, Client, _to_user_match


@pytest.fixture(scope="module")
def world() -> Dataset:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    return loaded.dataset


def test_any_two_clubs_can_be_told_apart(world: Dataset) -> None:
    clash = view.view_data()["kits"]["clash_distance"]
    changed = 0
    for home_id, away_id in permutations(sorted(world.clubs), 2):
        home, away = view.kits(world.club(home_id), world.club(away_id))
        assert home.shirt == world.club(home_id).color_primary.upper()  # home never changes
        colours = [home.shirt, away.shirt, home.keeper, away.keeper]
        for a, b in permutations(colours, 2):
            assert view.distance(a, b) >= clash, (home_id, away_id, colours)
        for kit in (home, away):
            assert view.distance(kit.shirt, kit.number) >= clash
        assert view.kits(world.club(home_id), world.club(away_id)) == (home, away)
        changed += away.shirt != world.club(away_id).color_primary.upper()
    assert changed > 0  # the sample has clubs in similar colours (two reds)


def test_shirt_numbers_are_unique_and_fall_back_to_the_slot(world: Dataset) -> None:
    squad = [p.id for p in world.squad("alvorada")]
    shirts = view.numbers(world, squad[:11], squad[11:18])
    assert len(set(shirts.values())) == 18
    assert view.numbers(world, ["x1", "x2"], ["x3"]) == {"x1": 1, "x2": 2, "x3": 3}


def _samples(frames: dict[str, Any]) -> list[tuple[int, ...]]:
    raw = base64.b64decode(frames["samples"])
    values = struct.unpack(f"<{len(raw) // 2}h", raw)
    assert len(values) == frames["count"] * WIDTH
    return [values[i:i + WIDTH] for i in range(0, len(values), WIDTH)]


@pytest.mark.positional
def test_the_pitch_and_the_chunks_of_a_live_match(tmp_path: Path) -> None:
    client = Client(tmp_path)
    client.call("career.new", name="campo", club_id="mineracao")
    _to_user_match(client)
    started = client.call("match.start")
    assert "frames" not in started
    pitch = started["pitch"]
    assert (pitch["length_cm"], pitch["width_cm"], pitch["hz"]) == (10500, 6800, 2)
    for side, first in (("home", 0), ("away", 11)):
        players = pitch[side]["players"]
        assert [p["slot"] for p in players] == list(range(first, first + 11))
        assert sum(p["keeper"] for p in players) == 1
        everyone = players + pitch[side]["bench"]
        assert len({p["number"] for p in everyone}) == len(everyone)
        assert all(p["slot"] == -1 for p in pitch[side]["bench"])
    assert started["match"]["home_id"] == pitch["home"]["club_id"]

    assert "frames" not in client.call("match.advance", seconds=3.0)  # a 1.3 client asks for none
    samples: list[tuple[int, ...]] = []
    events: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    subs: list[dict[str, Any]] = []
    steps = [0.3, 7.5, 0.0, 61.0, 900.0, 1.0, 2500.0, 0.5, 4000.0, 4000.0]
    finished = False
    for seconds in steps:
        step = client.call("match.advance", seconds=seconds, frames_from=len(samples))
        frames = step["frames"]
        assert frames["first"] == len(samples)
        samples += _samples(frames)
        for name, seen in (("events", events), ("shots", shots), ("subs", subs)):
            assert all(frames["first"] <= m["sample"] < len(samples) for m in frames[name])
            seen += frames[name]
        assert step["state"]["time_s"] == pytest.approx(len(samples) / 2, abs=1.0)
        finished = step["finished"]
    assert finished
    state = client.call("match.state")
    goals = [e for e in events if e["kind"] in ("goal", "own_goal", "penalty_goal")]
    assert (goals[-1]["score"] if goals else [0, 0]) == state["score"]
    # asking again for something already sent repeats it, and changes nothing
    again = client.call("match.advance", seconds=0.0, frames_from=len(samples) - 10)["frames"]
    assert _samples(again) == samples[-10:]

    match_id = started["match"]["id"]
    client.call("match.finish")
    record = api.match_record(client.session.state["career"], match_id)
    assert record is not None
    assert tuple(samples) == record.samples
    assert [e["sample"] for e in events] == [sample for sample, _ in record.events]
    assert [(s["sample"], s["slot"], s["on_target"]) for s in shots] == list(record.shots)
    assert len(shots) > 0
    assert [(s["sample"], s["slot"], s["player_id"]) for s in subs] == list(record.subs)


@pytest.mark.positional
def test_asking_for_frames_does_not_change_the_match(tmp_path: Path) -> None:
    """Spec 008b SC-004 / FR-013."""
    watched = Client(tmp_path / "campo")
    watched.call("career.new", name="igual", club_id="mineracao")
    _to_user_match(watched)
    match_id = watched.call("match.start")["match"]["id"]
    seen = 0
    while True:
        step = watched.call("match.advance", seconds=240.0, frames_from=seen)
        seen += step["frames"]["count"]
        if step["finished"]:
            break
    watched.call("match.finish")
    served = watched.session.state["career"]

    world = api.load_dataset(SAMPLE).dataset
    assert world is not None
    direct = api.new_career(world, "igual", "mineracao", master_seed=served.master_seed)
    while True:
        stop = api.continue_career(direct, tmp_path / "direto")
        if stop.kind == "user_match":
            api.continue_career(direct, tmp_path / "direto")  # plays it in the background
            break
    assert served.season.results[match_id] == direct.season.results[match_id]
    record = api.match_record(served, match_id)
    assert record is not None and record == api.match_record(direct, match_id)


def _minute_at(clock: list[list[int]], sample: int) -> tuple[int, int]:
    row = [r for r in clock if r[0] <= sample][-1]
    return row[1], row[2]


@pytest.mark.positional
def test_a_played_match_can_be_watched_again(tmp_path: Path) -> None:
    """Spec 008b US3: the replay of the live match after full time, of a played match, after a
    save and a reload; nothing for a match without a record."""
    client = Client(tmp_path)
    client.call("career.new", name="rever", club_id="mineracao")
    _to_user_match(client)
    started = client.call("match.start")
    match_id = started["match"]["id"]
    step = client.call("match.advance", seconds=20000.0, frames_from=0)
    assert step["finished"]

    live = client.call("match.record")  # before Continuar: the live match as played
    assert live["frames"]["first"] == 0 and live["frames"]["count"] == step["frames"]["count"]
    assert live["frames"]["samples"] == step["frames"]["samples"]
    assert live["final_score"] == step["state"]["score"]
    assert live["match"]["id"] == match_id
    for side in ("home", "away"):  # the record's line-ups are the match's
        assert live["pitch"][side]["players"] == started["pitch"][side]["players"]
        assert live["pitch"][side]["kit"] == started["pitch"][side]["kit"]
    # the clock: one row per change of minute, and it agrees with the events' minutes
    clock = live["clock"]
    assert clock[0] == [0, 1, 0] and clock[-1][1] == 90
    assert [r[0] for r in clock] == sorted({r[0] for r in clock})
    assert any(r[1] == 45 and r[2] > 0 for r in clock)  # first-half stoppage time
    events = live["frames"]["events"]
    assert events
    for e in events:
        minute = (e["minute"]["base"], e["minute"]["added"])
        assert minute in (_minute_at(clock, e["sample"]), _minute_at(clock, e["sample"] - 1)), e

    client.call("match.finish")
    played = client.call("match.record", match_id=match_id)
    assert live["match"]["result"] is None and played["match"]["result"] is not None
    live["match"] = played["match"]  # the only difference: the match now has its result
    assert played == live
    client.call("career.save")
    again = Client(tmp_path)
    again.call("career.open", name="rever")
    assert again.call("match.record", match_id=match_id) == live

    career = again.session.state["career"]
    month = career.season.matches[match_id].kickoff.month
    days = again.call("view.calendar", month=month)
    mine = [d for d in days if d["user_match"] is not None]
    assert [d["user_match_replay"] for d in mine if d["user_match"]["id"] == match_id] == [True]
    assert any(not d["user_match_replay"] for d in days)  # days with no match, or not played yet
    background = next(mid for mid, m in sorted(career.season.matches.items())
                      if mid in career.season.results
                      and career.user_club_id not in (m.home_id, m.away_id))
    assert again.call("match.record", match_id=background) is None
    assert again.error("match.record", match_id="nao-existe")["data"]["kind"] == "match"
