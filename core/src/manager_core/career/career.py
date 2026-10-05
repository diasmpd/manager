"""The career: a world, the current season, its history and the game loop (spec 004)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from manager_core.career.discipline import Discipline
from manager_core.career.recorded import RecordedProvider
from manager_core.competition.results import Result
from manager_core.competition.rules import load_ruleset_text, ruleset_text
from manager_core.competition.season import Season, SeasonEvent
from manager_core.competition.seeds import sub_seed
from manager_core.domain.dataset import Dataset
from manager_core.quicksim.provider import QuickSimProvider

USER_MATCH = "user_match"
EVENT = "event"
SEASON_END = "season_end"
STOP_EVENTS = frozenset({"draw", "stage_complete", "qualified", "paired", "relegated",
                         "champion", "title"})
AUTOSAVE_DAYS = 7


class UnknownClubError(LookupError):
    def __init__(self, club_id: str) -> None:
        super().__init__(club_id)
        self.club_id = club_id


@dataclass(frozen=True, slots=True)
class Stop:
    kind: str  # user_match / event / season_end
    day: date
    match_id: str | None = None
    events: tuple[SeasonEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class SeasonRecord:
    year: int
    champion: str
    runner_up: str
    side_titles: tuple[tuple[str, str], ...]  # (track, winner)
    relegated: tuple[str, ...]
    promoted: tuple[str, ...]
    final_classification: tuple[str, ...]
    top_scorers: tuple[tuple[str, str, int], ...]  # (player id, club id, goals)
    user_club: str
    user_place: int


@dataclass
class Career:
    name: str
    master_seed: int
    user_club_id: str
    current_date: date
    last_autosave: date
    world: Dataset  # at the start of the current season
    ruleset_toml: str
    season: Season
    history: list[SeasonRecord] = field(default_factory=list)
    pending: Stop | None = None
    selection: Any = None  # spec 005: the user's confirmed Selection (career.selection module)
    tactic: Any = None  # spec 006: the user's confirmed Tactic (tactics.model)
    notices: list[str] = field(default_factory=list)  # for the owner, shown once; not saved
    positional: bool = True  # spec 008: the user club's matches use the positional engine
    # spec 008: positional records of the user's matches, encoded, by (year, match id); the
    # current season's live ones are on the provider until stashed (save, rollover)
    records: dict[tuple[int, str], bytes] = field(default_factory=dict)

    def stash_records(self) -> None:
        provider = self.live_provider
        for match_id, record in provider.records.items():
            self.records[(self.season.year, match_id)] = record.encode()
        provider.records.clear()

    @property
    def live_provider(self) -> QuickSimProvider:
        provider = self.season.provider
        assert isinstance(provider, RecordedProvider)
        live = provider.live
        assert isinstance(live, QuickSimProvider)
        return live

    @property
    def year(self) -> int:
        return self.season.year


def default_seed(name: str) -> int:
    return sub_seed(0, f"career:{name}") % 2**31


def build_season(world: Dataset, ruleset_toml: str, year: int, master_seed: int,
                 participants: Sequence[str] | None,
                 recorded: Mapping[str, Result] | None = None) -> Season:
    """The season, deterministically from its definition; played matches come from
    `recorded` when given (loading a save) and from the quick sim otherwise."""
    ruleset = load_ruleset_text(ruleset_toml)
    provider = RecordedProvider(recorded or {}, QuickSimProvider(world))
    season = Season.start(world, ruleset, year, master_seed, participants, provider)
    season.discipline = Discipline(world)  # rebuilt from the results as they are (re)played
    return season


def new_career(world: Dataset, name: str, club_id: str, master_seed: int | None = None,
               ruleset_id: str = "mg-modulo-i-2026", year: int = 2027) -> Career:
    if club_id not in world.clubs:
        raise UnknownClubError(club_id)
    seed = default_seed(name) if master_seed is None else master_seed
    text = ruleset_text(ruleset_id)
    season = build_season(world, text, year, seed, None)
    if club_id not in season.participants:
        raise UnknownClubError(club_id)
    start = season.current_date
    return Career(name, seed, club_id, start, start, world, text, season)


def stop_to_json(stop: Stop | None) -> Any:
    if stop is None:
        return None
    return {"kind": stop.kind, "day": stop.day.isoformat(), "match_id": stop.match_id,
            "events": [[e.day.isoformat(), e.kind, list(e.payload)] for e in stop.events]}


def stop_from_json(data: Any) -> Stop | None:
    if data is None:
        return None
    return Stop(data["kind"], date.fromisoformat(data["day"]), data["match_id"],
                tuple(SeasonEvent(date.fromisoformat(d), k, tuple(p))
                      for d, k, p in data["events"]))


def record_to_json(r: SeasonRecord) -> Any:
    return {"year": r.year, "champion": r.champion, "runner_up": r.runner_up,
            "side_titles": [list(t) for t in r.side_titles], "relegated": list(r.relegated),
            "promoted": list(r.promoted), "final_classification": list(r.final_classification),
            "top_scorers": [list(s) for s in r.top_scorers], "user_club": r.user_club,
            "user_place": r.user_place}


def record_from_json(d: Any) -> SeasonRecord:
    return SeasonRecord(d["year"], d["champion"], d["runner_up"],
                        tuple((t, w) for t, w in d["side_titles"]), tuple(d["relegated"]),
                        tuple(d["promoted"]), tuple(d["final_classification"]),
                        tuple((p, c, g) for p, c, g in d["top_scorers"]), d["user_club"],
                        d["user_place"])


def _user_match_on(career: Career, day: date) -> str | None:
    for m in career.season.sorted_matches():
        if (m.kickoff.date() == day and m.id not in career.season.results
                and career.user_club_id in (m.home_id, m.away_id)):
            return m.id
    return None


def continue_(career: Career, autosave: Callable[[Career], None] | None = None,
              next_season: Callable[[Career], None] | None = None) -> Stop:
    """Advance day by day to the next stop (research R4): before the user's match day, after
    a day with a competition event, or at the season end. A season-end stop is followed, on
    the next call, by the rollover to the next season (`next_season`)."""
    if career.pending is not None and career.pending.kind == SEASON_END:
        if next_season is None:
            raise RuntimeError("no rollover available")
        next_season(career)
        career.pending = None
    while True:
        season = career.season
        if season.complete:
            career.pending = Stop(SEASON_END, career.current_date)
            return career.pending
        day = career.current_date + timedelta(days=1)
        if day.year != season.year:
            raise RuntimeError(f"season {season.year} not finished by 31 December")
        match_id = _user_match_on(career, day)
        pending = career.pending
        already_stopped = (pending is not None and pending.kind == USER_MATCH
                           and pending.day == day)
        if match_id is not None and not already_stopped:
            career.pending = Stop(USER_MATCH, day, match_id)
            return career.pending
        events = season.advance_to(day)
        career.current_date = day
        career.pending = None
        if autosave is not None and (day - career.last_autosave).days >= AUTOSAVE_DAYS:
            career.last_autosave = day
            autosave(career)
        if any(e.kind in STOP_EVENTS for e in events):
            career.pending = Stop(EVENT, day, None, tuple(events))
            return career.pending
