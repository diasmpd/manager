"""`build` (spec 011 T014): the cached pages -> a 001 dataset and its import report. Offline: it
reads only the cache. Deterministic: the same cache and inputs give the same bytes.

The squads are each club's whole season list on ogol, players who have since left included:
the game plays the Mineiro, and a state-league club's October page shows only the few players
still under contract. A player listed at several clubs plays for the one he is still at, or,
when he is at none, for the one he played most games for that season.
"""

from __future__ import annotations

import statistics
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any

from manager_core.domain.attributes import Attributes
from manager_core.domain.club import Club, ExternalRef
from manager_core.domain.dataset import Dataset, FlagKind, RecordFlag, RecordType, Source
from manager_core.domain.player import Player
from manager_core.domain.positions import Position, PositionFamiliarity
from manager_core.domain.squad import SquadMembership
from manager_core.io import reader, writer
from manager_core.ratings.ability import current_ability
from manager_core.realdata import mapping, synthesis
from manager_core.realdata.fetch import Fetcher
from manager_core.realdata.sources import ogol
from manager_core.sample.generator import HEIGHT_BY_POSITION

TOOL = "manager_core.realdata"
TOOL_VERSION = "0.1.0"
FORMAT_VERSION = "1.0"
OGOL_LICENCE = "ogol: no published terms; private use only, used gently (owner decision 2026-10-07)"
COMPETITIONS = {"mineiro-1": 1, "mineiro-2": 2}
AGES = (14, 45)  # the 001 format's player ages on the reference date (E011)


@dataclass
class ClubReport:
    club_id: str
    listed: int = 0
    players: int = 0
    missing_pages: int = 0
    defaulted: Counter[str] = field(default_factory=Counter)
    confidence: Counter[str] = field(default_factory=Counter)
    moved: list[str] = field(default_factory=list)  # listed here, playing elsewhere
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BuildResult:
    out: Path
    errors: tuple[str, ...]
    clubs: tuple[ClubReport, ...]


class _Cache:
    """The ogol cache, read-only: a page missing from it is None, never a fetch."""

    def __init__(self, cache_dir: Path) -> None:
        self.fetcher = Fetcher(cache_dir)

    def get(self, url: str) -> str | None:
        if not self.fetcher.cache_path(url).exists():
            return None
        return self.fetcher.get(url)


def _club_url(club: dict[str, Any], season_id: int) -> str:
    return f"{ogol.BASE}{club['ogol']}?epoca_id={season_id}"


def _player_url(entry: ogol.SquadEntry, season_id: int) -> str:
    return f"{ogol.BASE}/jogador/{entry.slug}/{entry.ogol_id}?epoca_id={season_id}"


def _season_games(raw: ogol.RawPlayer | None, season: int, club_path: str) -> tuple[int, int]:
    """(games, goals) for the club in the season."""
    if raw is None:
        return 0, 0
    lines = [s for s in raw.career
             if s.season.startswith(str(season)) and s.team_path == club_path]
    return sum(s.games for s in lines), sum(s.goals for s in lines)


def _retrieved_on(cache_dir: Path) -> date:
    log = cache_dir / "log.csv"
    stamps = [line.split(";")[1][:10] for line in log.read_text("utf-8").splitlines()[1:]
              if line.count(";") >= 3] if log.exists() else []
    return date.fromisoformat(max(stamps)) if stamps else date.today()


def _abbreviation(club_id: str) -> str:
    letters = "".join(c for c in club_id.upper() if c.isalpha())
    return (letters + "XXX")[:3]


def build(data_repo: Path, out: Path, competition: str = "mineiro-1") -> BuildResult:
    inputs = tomllib.loads((data_repo / "inputs" / "mineiro.toml").read_text("utf-8"))
    season = int(inputs["season"])
    season_id = int(inputs["ogol_season"])
    reference_date = date.fromisoformat(str(inputs.get("reference_date", f"{season}-01-15")))
    cache_dir = data_repo / "cache" / "ogol"
    cache = _Cache(cache_dir)
    module = COMPETITIONS[competition]
    club_inputs = [c for c in inputs["clubs"] if int(c["module"]) == module]

    reports = {c["club_id"]: ClubReport(c["club_id"]) for c in club_inputs}
    raw_clubs: dict[str, ogol.RawClub] = {}
    listings: dict[int, list[tuple[str, ogol.SquadEntry]]] = defaultdict(list)
    errors: list[str] = []
    for club in club_inputs:
        page = cache.get(_club_url(club, season_id))
        if page is None:
            errors.append(f"{club['club_id']}: club page not in the cache (run collect)")
            continue
        parsed = ogol.parse_club(page)
        raw_clubs[club["club_id"]] = parsed
        reports[club["club_id"]].listed = len(parsed.squad)
        for entry in parsed.squad:
            listings[entry.ogol_id].append((club["club_id"], entry))

    raw_players: dict[int, ogol.RawPlayer | None] = {}
    for ogol_id, listed in listings.items():
        page = cache.get(_player_url(listed[0][1], season_id))
        raw_players[ogol_id] = ogol.parse_player(page, ogol_id) if page is not None else None

    path_of = {c["club_id"]: c["ogol"].split("?")[0] for c in club_inputs}
    # each player's club: where he still is, else where he played most this season
    home: dict[int, tuple[str, ogol.SquadEntry]] = {}
    for ogol_id, listed in sorted(listings.items()):
        active = [item for item in listed if item[1].active]
        if active:
            choice = active[0]
        else:
            order = [c["club_id"] for c in club_inputs]
            choice = max(listed, key=lambda item: (
                _season_games(raw_players[ogol_id], season, path_of[item[0]])[0],
                -order.index(item[0])))
        home[ogol_id] = choice
        for club_id, _entry in listed:
            if club_id != choice[0]:
                reports[club_id].moved.append(f"p-og{ogol_id} -> {choice[0]}")

    by_club: dict[str, list[int]] = defaultdict(list)
    for ogol_id, (club_id, _entry) in home.items():
        by_club[club_id].append(ogol_id)

    players: dict[str, Player] = {}
    memberships: dict[str, SquadMembership] = {}
    flags: list[RecordFlag] = []
    reputation = synthesis.params()["club_reputation"]
    clubs: dict[str, Club] = {}
    for club in club_inputs:
        cid = club["club_id"]
        raw_club = raw_clubs.get(cid)
        if raw_club is None:
            continue
        report = reports[cid]
        ids = sorted(by_club[cid])
        games = {i: _season_games(raw_players[i], season, path_of[cid]) for i in ids}
        most_games = max((g for g, _ in games.values()), default=0)
        values = [v for i in ids if (v := home[i][1].market_value_eur)]
        median_value = statistics.median(values) if values else None
        numbers = Counter(home[i][1].number for i in ids if home[i][1].number)
        for ogol_id in ids:
            entry = home[ogol_id][1]
            raw = raw_players[ogol_id]
            pid = f"p-og{ogol_id}"
            missing: list[str] = []
            if raw is None:
                report.missing_pages += 1
                missing.append("player page")
            slots = mapping.positions_from_label(raw.position if raw else None)
            if not slots:
                slots = [mapping.GROUP_POSITION.get(entry.group, Position.MC)]
                missing.append("position (from the squad section)")
            position = slots[0]
            if raw and raw.birth_date:
                born = date.fromisoformat(raw.birth_date)
            else:
                age = entry.age if entry.age is not None else 25
                born = date(reference_date.year - age, 7, 1)
                missing.append("birth date (from the age)" if entry.age else "birth date")
            age_then = reference_date.year - born.year - (
                (reference_date.month, reference_date.day) < (born.month, born.day))
            if not AGES[0] <= age_then <= AGES[1]:  # e.g. a veteran registered for one game
                report.notes.append(f"left out: {pid} ({entry.name}), aged {age_then}")
                continue
            nation_text = (raw.nationality if raw else None) or entry.nationality
            codes, unknown = mapping.nations(nation_text)
            if not codes:
                codes = ("BRA",)
                missing.append(f"nationality ({nation_text or 'none'})")
            elif unknown:
                missing.append(f"nationality ({', '.join(unknown)})")
            height = raw.height_cm if raw else None
            if height is None or not 150 <= height <= 210:
                height = HEIGHT_BY_POSITION.get(position, (180, 0))[0]
                missing.append("height")
            weight = raw.weight_kg if raw else None
            if weight is None or not 50 <= weight <= 110:
                weight = max(55, min(100, height - 104))
                if raw and raw.weight_kg is not None:
                    missing.append("weight")
            left, right = mapping.feet(raw.foot if raw else None, pid)
            played, goals = games[ogol_id]
            result = synthesis.synthesise(synthesis.Signals(
                player_id=pid, position=position, division=str(club["division"]),
                age=age_then,
                games_share=played / most_games if most_games else None,
                value_eur=entry.market_value_eur, club_median_value_eur=median_value,
                goals_per_game=goals / played if played else None))
            players[pid] = Player(
                id=pid,
                full_name=((raw.full_name if raw else None) or entry.name)[:80],
                display_name=entry.name[:30], date_of_birth=born, nationalities=codes,
                height_cm=height, weight_kg=weight, left_foot=left, right_foot=right,
                attributes=Attributes(**result.attributes),
                positions=PositionFamiliarity(mapping.familiarity(slots)),
                potential_ability=result.potential_ability,
                external_refs=(ExternalRef("ogol", str(ogol_id)),))
            # the game's CA can round a point above the synthesis target: PA is never below it
            ca = current_ability(players[pid])
            if players[pid].potential_ability < ca:
                players[pid] = replace(players[pid], potential_ability=ca)
            value = entry.market_value_eur
            number = entry.number if entry.number and numbers[entry.number] == 1 else None
            memberships[pid] = SquadMembership(
                pid, cid, shirt_number=number if number and 1 <= number <= 99 else None,
                market_value=value, currency="EUR" if value is not None else None)
            flags.append(RecordFlag(RecordType.PLAYER, pid, FlagKind.SYNTHESIS_CONFIDENCE,
                                    f"{result.confidence}: {result.reason}"))
            report.confidence[result.confidence] += 1
            if missing:
                flags.append(RecordFlag(RecordType.PLAYER, pid, FlagKind.INCOMPLETE,
                                        "; ".join(missing)))
                report.defaulted.update(m.split(" (")[0] for m in missing)
            report.players += 1
        colours = club.get("colors") or raw_club.colors or ("#FFFFFF", "#000000")
        founded = club.get("founded") or (raw_club.founded or "")[:4]
        club_missing = [name for name, value in (
            ("stadium", club.get("stadium") or raw_club.stadium),
            ("capacity", club.get("capacity") or raw_club.capacity),
            ("founded", founded), ("city", club.get("city") or raw_club.city),
            ("short_name", club.get("short_name")), ("abbreviation", club.get("abbreviation")),
        ) if not value]
        clubs[cid] = Club(
            id=cid,
            name=(club.get("name") or raw_club.name or cid)[:60],
            short_name=(club.get("short_name") or raw_club.name or cid)[:20],
            abbreviation=club.get("abbreviation") or _abbreviation(cid),
            city=(club.get("city") or raw_club.city or "?")[:60],
            state=club.get("state") or raw_club.state,
            country="BRA",
            color_primary=colours[0], color_secondary=colours[1],
            stadium_name=(club.get("stadium") or raw_club.stadium or "?")[:80],
            stadium_capacity=max(500, int(club.get("capacity") or raw_club.capacity or 500)),
            founded_year=int(founded) if str(founded).isdigit() else 1900,
            reputation=int(reputation.get(str(club["division"]), reputation["none"])),
            external_refs=(ExternalRef("ogol", club["ogol"].split("?")[0]),))
        if club_missing:
            flags.append(RecordFlag(RecordType.CLUB, cid, FlagKind.INCOMPLETE,
                                    "defaulted: " + ", ".join(club_missing)))
            report.notes.append("defaulted: " + ", ".join(club_missing))

    dataset = Dataset(
        format_version=FORMAT_VERSION, reference_date=reference_date, fictional=False,
        tool=TOOL, tool_version=TOOL_VERSION,
        sources=(Source("ogol", _retrieved_on(cache_dir), "https://www.ogol.com.br",
                        OGOL_LICENCE),),
        clubs=clubs, players=players, memberships=memberships,
        notes=(f"Real data, private: {competition} {season} "
               f"(model {synthesis.params()['model_version']})"),
        record_flags=tuple(flags))
    writer.write(dataset, out)
    loaded = reader.load(out)
    errors += [f"{issue.file}: {issue.code} {issue.message}" for issue in loaded.report.errors]
    _write_report(out, dataset, list(reports.values()), errors)
    return BuildResult(out, tuple(errors), tuple(reports.values()))


def _strength(dataset: Dataset, club_id: str, size: int = 16) -> float:
    """The mean CA of the club's best `size` players."""
    cas = sorted((current_ability(dataset.players[m.player_id])
                  for m in dataset.memberships.values() if m.club_id == club_id), reverse=True)
    top = cas[:size]
    return sum(top) / len(top) if top else 0.0


def _write_report(out: Path, dataset: Dataset, reports: list[ClubReport],
                  errors: list[str]) -> None:
    sources = ", ".join(f"{s.name} (retrieved {s.retrieved_on})" for s in dataset.sources)
    lines = [
        "# Import report", "",
        f"- Dataset: {dataset.notes}",
        f"- Reference date: {dataset.reference_date.isoformat()}",
        f"- Sources: {sources}",
        f"- Clubs: {len(dataset.clubs)}, players: {len(dataset.players)}",
        f"- Validation errors: {len(errors)}", "",
        "| Club | Listed | Players | Strength (top-16 CA) | Confidence h/m/l | Defaulted |",
        "|---|---|---|---|---|---|",
    ]
    ranked = sorted(reports, key=lambda r: -_strength(dataset, r.club_id)
                    if r.club_id in dataset.clubs else 0.0)
    for r in ranked:
        if r.club_id not in dataset.clubs:
            lines.append(f"| {r.club_id} | - | - | - | - | club page missing |")
            continue
        conf = "/".join(str(r.confidence[k]) for k in ("high", "medium", "low"))
        defaulted = ", ".join(f"{k} {v}" for k, v in sorted(r.defaulted.items())) or "-"
        lines.append(f"| {r.club_id} | {r.listed} | {r.players} | "
                     f"{_strength(dataset, r.club_id):.1f} | {conf} | {defaulted} |")
    lines += ["", "## Per club", ""]
    for r in reports:
        lines.append(f"### {r.club_id}")
        lines.append(f"- Missing player pages: {r.missing_pages}")
        lines.append(f"- Listed here, playing elsewhere: {len(r.moved)}"
                     + (f" ({', '.join(r.moved)})" if r.moved else ""))
        lines += [f"- {note}" for note in r.notes]
        lines.append("")
    if errors:
        lines += ["## Errors", "", *(f"- {e}" for e in errors), ""]
    (out / "import-report.md").write_text("\n".join(lines), "utf-8", newline="\n")
