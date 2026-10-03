"""Competition rulesets as data (FR-001..007, contracts/ruleset-format.md).

A ruleset is a TOML file. The loader validates the whole file first and reports every problem
(R-codes, data-model.md) before building any object, like the 001 importer.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Any, TypeVar

from manager_core.i18n import t

FORMAT_VERSION = 1
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class Tiebreaker(StrEnum):
    WINS = "wins"
    GOAL_DIFFERENCE = "goal_difference"
    GOALS_FOR = "goals_for"
    HEAD_TO_HEAD = "head_to_head"
    FEWER_RED_CARDS = "fewer_red_cards"
    FEWER_YELLOW_CARDS = "fewer_yellow_cards"
    DRAW = "draw"


class Matching(StrEnum):
    OWN_GROUP = "own_group"
    OTHER_GROUPS = "other_groups"
    ALL = "all"


class DrawMethod(StrEnum):
    POTS_BY_REPUTATION = "pots_by_reputation"
    FIXED = "fixed"


class EntrantKind(StrEnum):
    GROUP_WINNERS = "group_winners"
    BEST_OF_PLACE = "best_of_place"
    OVERALL_PLACES = "overall_places"
    WINNERS_OF = "winners_of"


class Pairing(StrEnum):
    CAMPAIGN_1V4_2V3 = "campaign_1v4_2v3"
    CAMPAIGN_HIGH_LOW = "campaign_high_low"


class TieRule(StrEnum):
    PENALTIES = "penalties"
    POINTS_THEN_CAMPAIGN = "points_then_campaign"


class Venue(StrEnum):
    HOME = "home"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class Scoring:
    win: int
    draw: int
    loss: int
    tiebreakers: tuple[Tiebreaker, ...]


@dataclass(frozen=True, slots=True)
class CalendarRule:
    window_start: tuple[int, int]  # (month, day)
    window_end: tuple[int, int]
    weekend_days: tuple[int, ...]  # Monday = 0
    midweek_days: tuple[int, ...]
    kickoff_weekend: time
    kickoff_midweek: time
    min_rest_hours: int
    avoid_windows: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NeutralVenue:
    name: str
    city: str
    capacity: int


@dataclass(frozen=True, slots=True)
class EntrantRule:
    source: str
    kind: EntrantKind
    place: int | None = None
    count: int | None = None
    places: tuple[int, int] | None = None
    exclude_tracks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OutcomeRule:
    kind: str  # "relegated"
    places: tuple[int, int]


@dataclass(frozen=True, slots=True)
class GroupStageRule:
    id: str
    group_count: int
    group_size: int
    matching: Matching
    rounds: int
    draw: DrawMethod
    fixed_groups: tuple[tuple[str, ...], ...] = ()
    outcomes: tuple[OutcomeRule, ...] = ()
    name: str | None = None  # in-game display name (data, like club names)


@dataclass(frozen=True, slots=True)
class KnockoutStageRule:
    id: str
    track: str
    legs: int
    entrants: tuple[EntrantRule, ...]
    pairing: Pairing
    tie_rule: TieRule
    venue: Venue
    title: str | None = None
    deciding_leg_host: str = "better_campaign"
    dates_with: str | None = None
    may_exceed_window: bool = False
    name: str | None = None


StageRule = GroupStageRule | KnockoutStageRule


@dataclass(frozen=True, slots=True)
class Ruleset:
    id: str
    name: str
    short_name: str
    state: str
    country: str
    regulation_year: int
    valid_from: int
    valid_to: int | None
    participants: int
    scoring: Scoring
    calendar: CalendarRule
    neutral_venue: NeutralVenue | None
    stages: tuple[StageRule, ...]

    def is_valid_for(self, year: int) -> bool:
        return self.valid_from <= year and (self.valid_to is None or year <= self.valid_to)

    def stage(self, stage_id: str) -> StageRule:
        return next(s for s in self.stages if s.id == stage_id)

    @property
    def group_stage(self) -> GroupStageRule:
        return next(s for s in self.stages if isinstance(s, GroupStageRule))

    @property
    def knockout_stages(self) -> tuple[KnockoutStageRule, ...]:
        return tuple(s for s in self.stages if isinstance(s, KnockoutStageRule))

    def stage_name(self, stage_id: str) -> str:
        return self.stage(stage_id).name or stage_id

    def tracks(self) -> tuple[str, ...]:
        """Knockout tracks in declaration order (`main` is the championship itself)."""
        return tuple(dict.fromkeys(s.track for s in self.knockout_stages))

    def track_title(self, track: str) -> str:
        """The title the track awards (the `title` of its final stage), or the track id."""
        return next((s.title for s in self.knockout_stages if s.track == track and s.title),
                    track)

    def first_stage_of(self, track: str) -> KnockoutStageRule:
        return next(s for s in self.knockout_stages if s.track == track)


@dataclass(frozen=True, slots=True)
class RulesetIssue:
    code: str
    path: str
    message: str


@dataclass
class RulesetReport:
    source: str
    issues: list[RulesetIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, code: str, path: str, /, **params: object) -> None:
        self.issues.append(RulesetIssue(code, path, t(f"ruleset.{code}", path=path, **params)))


class RulesetError(Exception):
    def __init__(self, report: RulesetReport) -> None:
        super().__init__("; ".join(f"{i.code} {i.path}" for i in report.issues))
        self.report = report


class RulesetNotFoundError(LookupError):
    def __init__(self, ruleset_id: str) -> None:
        super().__init__(ruleset_id)
        self.ruleset_id = ruleset_id


@dataclass(frozen=True, slots=True)
class RulesetSummary:
    id: str
    name: str
    state: str
    valid_from: int
    valid_to: int | None


# ---- loading -------------------------------------------------------------------------------

T = TypeVar("T")
_MISSING = object()


class _Reader:
    """Typed access to the parsed TOML that records R002/R003 instead of raising."""

    def __init__(self, report: RulesetReport) -> None:
        self.report = report

    def get(self, table: dict[str, Any], key: str, kind: type[T], path: str,
            default: Any = _MISSING) -> T | None:
        if key not in table:
            if default is _MISSING:
                self.report.add("R002", f"{path}.{key}" if path else key, expected=kind.__name__)
            return None if default is _MISSING else default
        value = table[key]
        ok = isinstance(value, kind) and not (kind is int and isinstance(value, bool))
        if not ok:
            self.report.add("R002", f"{path}.{key}" if path else key, expected=kind.__name__)
            return None
        return value  # type: ignore[no-any-return]

    def enum(self, table: dict[str, Any], key: str, enum: type[T], path: str,
             default: Any = _MISSING) -> T | None:
        raw = self.get(table, key, str, path, default)
        if raw is None:
            return None
        if isinstance(raw, enum):
            return raw
        try:
            return enum(raw)  # type: ignore[call-arg]
        except ValueError:
            self.report.add("R003", f"{path}.{key}", value=raw)
            return None


def _month_day(raw: str | None) -> tuple[int, int] | None:
    if raw is None:
        return None
    try:
        month, day = (int(p) for p in raw.split("-"))
    except ValueError:
        return None
    return (month, day) if 1 <= month <= 12 and 1 <= day <= 31 else None


def _clock(raw: str | None) -> time | None:
    if raw is None:
        return None
    try:
        hour, minute = (int(p) for p in raw.split(":"))
        return time(hour, minute)
    except ValueError:
        return None


def _parse(doc: dict[str, Any], report: RulesetReport) -> Ruleset | None:
    r = _Reader(report)
    version = r.get(doc, "format_version", int, "")
    if version is not None and version > FORMAT_VERSION:
        report.add("R002", "format_version", expected=f"<= {FORMAT_VERSION}")

    comp = r.get(doc, "competition", dict, "") or {}
    cid = r.get(comp, "id", str, "competition")
    name = r.get(comp, "name", str, "competition")
    short = r.get(comp, "short_name", str, "competition")
    state = r.get(comp, "state", str, "competition")
    country = r.get(comp, "country", str, "competition")
    participants = r.get(comp, "participants", int, "competition")
    regulation_year = r.get(comp, "regulation_year", int, "competition")
    valid_from = r.get(comp, "valid_from", int, "competition")
    valid_to = r.get(comp, "valid_to", int, "competition", default=None)
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        report.add("R013", "competition.valid_to")

    sc = r.get(doc, "scoring", dict, "") or {}
    points = [r.get(sc, k, int, "scoring") for k in ("win", "draw", "loss")]
    raw_tb = r.get(sc, "tiebreakers", list, "scoring") or []
    tiebreakers: list[Tiebreaker] = []
    for i, raw in enumerate(raw_tb):
        try:
            tiebreakers.append(Tiebreaker(raw))
        except ValueError:
            report.add("R003", f"scoring.tiebreakers[{i}]", value=raw)
    if raw_tb and (Tiebreaker.DRAW not in tiebreakers or tiebreakers[-1] is not Tiebreaker.DRAW):
        report.add("R009", "scoring.tiebreakers")

    cal = r.get(doc, "calendar", dict, "") or {}
    start = _month_day(r.get(cal, "window_start", str, "calendar"))
    end = _month_day(r.get(cal, "window_end", str, "calendar"))
    if start is None or end is None or end <= start:
        report.add("R010", "calendar.window")

    def days(key: str) -> tuple[int, ...]:
        names = r.get(cal, key, list, "calendar") or []
        values = []
        for n in names:
            if n not in WEEKDAYS:
                report.add("R003", f"calendar.{key}", value=n)
            else:
                values.append(WEEKDAYS[n])
        return tuple(values)

    weekend, midweek = days("weekend_days"), days("midweek_days")
    k_weekend = _clock(r.get(cal, "kickoff_weekend", str, "calendar"))
    k_midweek = _clock(r.get(cal, "kickoff_midweek", str, "calendar"))
    rest = r.get(cal, "min_rest_hours", int, "calendar")
    if rest is not None and rest < 0:
        report.add("R010", "calendar.min_rest_hours")
    avoid = tuple(r.get(cal, "avoid_windows", list, "calendar", default=[]) or [])
    if None in (k_weekend, k_midweek):
        report.add("R002", "calendar.kickoff", expected="HH:MM")
    elif rest is not None and weekend and midweek:
        _check_rest_feasible(report, weekend, midweek, k_weekend, k_midweek, rest)  # type: ignore[arg-type]

    venues = r.get(doc, "venues", dict, "", default={}) or {}
    neutral = None
    if "neutral" in venues:
        nv = r.get(venues, "neutral", dict, "venues") or {}
        nv_name = r.get(nv, "name", str, "venues.neutral")
        nv_city = r.get(nv, "city", str, "venues.neutral")
        nv_cap = r.get(nv, "capacity", int, "venues.neutral")
        if nv_name and nv_city and nv_cap:
            neutral = NeutralVenue(nv_name, nv_city, nv_cap)

    stages = _parse_stages(r, doc, participants, neutral is not None)
    if not report.ok:
        return None
    assert cid and name and short and state and country and participants
    assert regulation_year and valid_from and start and end and rest is not None
    assert k_weekend and k_midweek and all(p is not None for p in points)
    return Ruleset(
        id=cid, name=name, short_name=short, state=state, country=country,
        regulation_year=regulation_year, valid_from=valid_from, valid_to=valid_to,
        participants=participants,
        scoring=Scoring(points[0], points[1], points[2], tuple(tiebreakers)),  # type: ignore[arg-type]
        calendar=CalendarRule(start, end, weekend, midweek, k_weekend, k_midweek, rest, avoid),
        neutral_venue=neutral, stages=tuple(stages),
    )


def _check_rest_feasible(report: RulesetReport, weekend: tuple[int, ...],
                         midweek: tuple[int, ...], k_weekend: time, k_midweek: time,
                         rest: int) -> None:
    """R014: after any midweek match there must be a legal weekend day, and vice versa."""
    def hours(day_a: int, t_a: time, day_b: int, t_b: time) -> float:
        gap_days = (day_b - day_a) % 7 or 7
        return gap_days * 24 + (t_b.hour - t_a.hour) + (t_b.minute - t_a.minute) / 60

    for m in midweek:
        if not any(hours(m, k_midweek, w, k_weekend) >= rest for w in weekend):
            report.add("R014", "calendar", hours=rest)
            return
    for w in weekend:
        if not any(hours(w, k_weekend, m, k_midweek) >= rest for m in midweek):
            report.add("R014", "calendar", hours=rest)
            return


def _places(raw: Any) -> tuple[int, int] | None:
    if (isinstance(raw, list) and len(raw) == 2 and all(isinstance(v, int) for v in raw)
            and raw[0] <= raw[1]):
        return (raw[0], raw[1])
    return None


def _parse_stages(r: _Reader, doc: dict[str, Any], participants: int | None,
                  has_neutral: bool) -> list[StageRule]:
    report = r.report
    raw_stages = r.get(doc, "stages", list, "") or []
    stages: list[StageRule] = []
    seen: dict[str, int] = {}
    entrants_per_stage: dict[str, int] = {}
    group_counts: dict[str, int] = {}
    track_sources: dict[str, list[EntrantRule]] = {}  # track -> its entrant rules
    n = participants or 0

    for i, raw in enumerate(raw_stages):
        path = f"stages[{i}]"
        if not isinstance(raw, dict):
            report.add("R002", path, expected="table")
            continue
        sid = r.get(raw, "id", str, path) or f"#{i}"
        kind = r.get(raw, "type", str, path)
        if kind == "groups":
            stage = _parse_group_stage(r, raw, path, sid, n)
            if stage:
                stages.append(stage)
                entrants_per_stage[sid] = n
                group_counts[sid] = stage.group_count
        elif kind == "knockout":
            stage_k = _parse_knockout(r, raw, path, sid, n, seen, entrants_per_stage,
                                      group_counts, has_neutral, track_sources)
            if stage_k:
                stages.append(stage_k)
        elif kind is not None:
            report.add("R003", f"{path}.type", value=kind)
        seen[sid] = i
    if not stages and raw_stages:
        report.add("R002", "stages", expected="stage tables")
    return stages


def _parse_group_stage(r: _Reader, raw: dict[str, Any], path: str, sid: str,
                       n: int) -> GroupStageRule | None:
    report = r.report
    count = r.get(raw, "group_count", int, path)
    size = r.get(raw, "group_size", int, path)
    matching = r.enum(raw, "matching", Matching, path)
    rounds = r.get(raw, "rounds", int, path)
    draw = r.enum(raw, "draw", DrawMethod, path)
    if count and size and n and count * size != n:
        report.add("R004", path, groups=count, size=size, participants=n)
    if matching is Matching.OTHER_GROUPS and count is not None and count < 2:
        report.add("R011", f"{path}.matching")
    if rounds is not None and rounds not in (1, 2):
        report.add("R003", f"{path}.rounds", value=rounds)
    fixed: tuple[tuple[str, ...], ...] = ()
    if draw is DrawMethod.FIXED:
        groups = r.get(raw, "groups", list, path) or []
        fixed = tuple(tuple(g) for g in groups)
    outcomes = []
    for j, o in enumerate(r.get(raw, "outcomes", list, path, default=[]) or []):
        places = _places(o.get("overall_places")) if isinstance(o, dict) else None
        if not isinstance(o, dict) or o.get("kind") != "relegated" or places is None:
            report.add("R002", f"{path}.outcomes[{j}]", expected="relegated + overall_places")
            continue
        if not 1 <= places[0] <= places[1] <= n:
            report.add("R006", f"{path}.outcomes[{j}]", places=f"{places[0]}–{places[1]}")
        outcomes.append(OutcomeRule("relegated", places))
    name = r.get(raw, "name", str, path, default=None)
    if None in (count, size, matching, rounds, draw):
        return None
    assert count and size and matching and rounds and draw
    return GroupStageRule(sid, count, size, matching, rounds, draw, fixed, tuple(outcomes), name)


def _parse_knockout(r: _Reader, raw: dict[str, Any], path: str, sid: str, n: int,
                    seen: dict[str, int], entrants_per_stage: dict[str, int],
                    group_counts: dict[str, int], has_neutral: bool,
                    track_sources: dict[str, list[EntrantRule]]) -> KnockoutStageRule | None:
    report = r.report
    track = r.get(raw, "track", str, path)
    legs = r.get(raw, "legs", int, path)
    pairing = r.enum(raw, "pairing", Pairing, path)
    tie_rule = r.enum(raw, "tie_rule", TieRule, path)
    venue = r.enum(raw, "venue", Venue, path)
    title = r.get(raw, "title", str, path, default=None)
    name = r.get(raw, "name", str, path, default=None)
    dates_with = r.get(raw, "dates_with", str, path, default=None)
    exceed = r.get(raw, "may_exceed_window", bool, path, default=False)
    if legs is not None and legs not in (1, 2):
        report.add("R003", f"{path}.legs", value=legs)
    if venue is Venue.NEUTRAL and not has_neutral:
        report.add("R008", f"{path}.venue")
    if dates_with is not None and dates_with not in seen:
        report.add("R005", f"{path}.dates_with", ref=dates_with)

    entrants: list[EntrantRule] = []
    total = 0
    broken = False  # an entrant rule was rejected: its count is unknown, skip R007
    for j, e in enumerate(r.get(raw, "entrants", list, path) or []):
        epath = f"{path}.entrants[{j}]"
        if not isinstance(e, dict):
            report.add("R002", epath, expected="table")
            broken = True
            continue
        source = r.get(e, "from", str, epath)
        kind = r.enum(e, "rule", EntrantKind, epath)
        if source is not None and source not in seen:
            report.add("R005", f"{epath}.from", ref=source)
            broken = True
            continue
        if source is None or kind is None:
            broken = True
            continue
        exclude = tuple(r.get(e, "exclude_tracks", list, epath, default=[]) or [])
        entrant = EntrantRule(source, kind, exclude_tracks=exclude)
        if kind is EntrantKind.GROUP_WINNERS:
            total += group_counts.get(source, 0)
        elif kind is EntrantKind.BEST_OF_PLACE:
            place = r.get(e, "place", int, epath)
            count = r.get(e, "count", int, epath)
            entrant = EntrantRule(source, kind, place=place, count=count, exclude_tracks=exclude)
            total += count or 0
        elif kind is EntrantKind.OVERALL_PLACES:
            places = _places(e.get("places"))
            if places is None or not 1 <= places[0] <= places[1] <= n:
                report.add("R006", f"{epath}.places", places=str(e.get("places")))
                broken = True
            else:
                entrant = EntrantRule(source, kind, places=places, exclude_tracks=exclude)
                total += places[1] - places[0] + 1
        elif kind is EntrantKind.WINNERS_OF:
            total += entrants_per_stage.get(source, 0) // 2
        entrants.append(entrant)
        if track is not None:
            _check_overlap(report, epath, track, entrant, track_sources)

    # a power of two, so every track ends in a single final
    if not broken and (total < 2 or total & (total - 1)):
        report.add("R007", f"{path}.entrants", count=total)
    entrants_per_stage[sid] = total
    if None in (track, legs, pairing, tie_rule, venue):
        return None
    assert track and legs and pairing and tie_rule and venue
    return KnockoutStageRule(sid, track, legs, tuple(entrants), pairing, tie_rule, venue, title,
                             "better_campaign", dates_with, bool(exceed), name)


def _check_overlap(report: RulesetReport, path: str, track: str, entrant: EntrantRule,
                   track_sources: dict[str, list[EntrantRule]]) -> None:
    """R012: an `overall_places` rule drawing from the same stage as another track's entrant
    rule could take the same club, unless it excludes that track or both are `overall_places`
    with disjoint ranges."""
    if entrant.kind is EntrantKind.WINNERS_OF:
        return
    for other, rules in track_sources.items():
        if other == track or other in entrant.exclude_tracks:
            continue
        for rule in rules:
            if rule.source != entrant.source or track in rule.exclude_tracks:
                continue
            if EntrantKind.OVERALL_PLACES not in (rule.kind, entrant.kind):
                continue
            if (rule.places and entrant.places
                    and (rule.places[1] < entrant.places[0] or entrant.places[1] < rule.places[0])):
                continue
            report.add("R012", path, track=other)
            break
    track_sources.setdefault(track, []).append(entrant)


def _load(text_loader: Callable[[], str], source: str) -> Ruleset:
    report = RulesetReport(source)
    try:
        doc = tomllib.loads(text_loader())
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        report.add("R001", source, detail=str(exc))
        raise RulesetError(report) from exc
    ruleset = _parse(doc, report)
    if ruleset is None or not report.ok:
        raise RulesetError(report)
    return ruleset


def _bundled() -> Any:
    return resources.files("manager_core.reference").joinpath("competitions")


def load_ruleset(ruleset_id: str) -> Ruleset:
    entry = _bundled().joinpath(f"{ruleset_id}.toml")
    if not entry.is_file():
        raise RulesetNotFoundError(ruleset_id)
    return _load(lambda: entry.read_text("utf-8"), f"{ruleset_id}.toml")


def load_ruleset_file(path: Path) -> Ruleset:
    return _load(lambda: path.read_text("utf-8"), str(path))


def validate_ruleset_file(path: Path) -> RulesetReport:
    try:
        load_ruleset_file(path)
    except RulesetError as exc:
        return exc.report
    return RulesetReport(str(path))


def list_rulesets() -> list[RulesetSummary]:
    result = []
    for entry in sorted(_bundled().iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".toml"):
            r = load_ruleset(entry.name[: -len(".toml")])
            result.append(RulesetSummary(r.id, r.name, r.state, r.valid_from, r.valid_to))
    return result
