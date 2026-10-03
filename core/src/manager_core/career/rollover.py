"""Season rollover (spec 004 FR-011..FR-014, research R6-R9).

At the end of a season the career:
1. records the season's history;
2. drops the relegated clubs from the next season and generates two promoted clubs;
3. ages every player a year (the world's reference date moves on);
4. develops players along a placeholder age curve;
5. lets players decide to retire;
6. refills each participating squad with generated youngsters;
7. starts the next season.

Every random draw comes from `sub_seed(career seed, "rollover:<year>:<step>")`, and players and
clubs are always visited in sorted order (Constitution II).
"""

from __future__ import annotations

import dataclasses
import math
import random
import tomllib
import unicodedata
from collections import Counter
from functools import cache
from importlib import resources
from typing import Any

from manager_core.career.career import Career, SeasonRecord, build_season
from manager_core.competition.seeds import sub_seed
from manager_core.domain.attributes import ATTRIBUTE_GROUPS, AttributeGroup
from manager_core.domain.club import Club
from manager_core.domain.dataset import Dataset
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.domain.squad import SquadMembership
from manager_core.ratings.ability import best_position, current_ability, is_goalkeeper
from manager_core.sample.generator import (
    SQUAD_SHAPE,
    TIER_QUALITY,
    assign_shirt_numbers,
    make_club,
    make_player,
)
from manager_core.sample.names import ClubIdentity

SQUAD_SIZE = len(SQUAD_SHAPE)
PROMOTED_PER_SEASON = 2
YOUTH_AGES = (16, 19)
CA_TO_ATTRIBUTE = 19 / 199  # derived CA (001 R8): CA = 1 + (S - 1) * 199 / 19
_VISIBLE_OUTFIELD = (ATTRIBUTE_GROUPS[AttributeGroup.TECHNICAL]
                     + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
                     + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL])
_VISIBLE_KEEPER = (ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]
                   + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
                   + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL])


@cache
def _reference(name: str) -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("career").joinpath(name)
    return tomllib.loads(entry.read_text("utf-8"))


def _band(bands: list[dict[str, Any]], age: int, key: str) -> float:
    return float(next(b[key] for b in bands if age <= b["max_age"]))


def _rng(career: Career, step: str) -> random.Random:
    return random.Random(sub_seed(career.master_seed, f"rollover:{career.season.year}:{step}"))


# ---- 1. history -------------------------------------------------------------------------------


def season_record(career: Career, promoted: tuple[str, ...]) -> SeasonRecord:
    season = career.season
    outcome = season.outcome()
    assert outcome is not None, "the season is not finished"
    goals: Counter[str] = Counter()
    club_of: dict[str, str] = {}
    for match_id in sorted(season.results):
        report = season.results[match_id].report
        if report is None:
            continue
        match = season.matches[match_id]
        for e in report.events:
            if e.kind in ("goal", "penalty_goal"):
                goals[e.player_id] += 1
                club_of[e.player_id] = match.home_id if e.side == "home" else match.away_id
    top = sorted(goals, key=lambda pid: (-goals[pid], pid))[:10]
    order = outcome.final_classification
    place = order.index(career.user_club_id) + 1 if career.user_club_id in order else 0
    return SeasonRecord(
        year=season.year, champion=outcome.champion, runner_up=outcome.runner_up,
        side_titles=tuple(sorted(outcome.side_titles.items())),
        relegated=tuple(outcome.relegated), promoted=promoted,
        final_classification=tuple(order),
        top_scorers=tuple((pid, club_of[pid], goals[pid]) for pid in top),
        user_club=career.user_club_id, user_place=place,
    )


# ---- 2. promoted clubs ------------------------------------------------------------------------


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _slug(text: str) -> str:
    return "-".join(_ascii(text).lower().split())


def _abbreviation(town: str, taken: set[str]) -> str:
    words = _ascii(town).upper().split()
    letters = "".join(w[0] for w in words) if len(words) >= 3 else "".join(words)
    base = "".join(c for c in letters if c.isalpha())
    options = [base[:3]] + [base[:2] + c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    return next(o for o in options if len(o) == 3 and o not in taken)


def promoted_identities(world: Dataset, generation: int) -> list[ClubIdentity]:
    """The two clubs promoted at this rollover (the generation-th rollover of the career)."""
    ref = _reference("promoted-clubs.toml")
    towns, prefixes, colours = ref["towns"], ref["prefixes"], ref["colours"]
    taken_ids = set(world.clubs)
    taken_abbr = {c.abbreviation for c in world.clubs.values()}
    identities = []
    for k in range(PROMOTED_PER_SEASON):
        n = generation * PROMOTED_PER_SEASON + k
        town = towns[n % len(towns)]
        cycle = n // len(towns)
        suffix = "" if cycle == 0 else " " + "I" * (cycle + 1)
        club_id = _slug(town) + ("" if cycle == 0 else f"-{cycle + 1}")
        while club_id in taken_ids:
            club_id += "-x"
        abbreviation = _abbreviation(town, taken_abbr)
        primary, secondary = colours[n % len(colours)]
        rng = random.Random(sub_seed(0, f"promoted:{club_id}"))
        identities.append(ClubIdentity(
            id=club_id, name=f"{prefixes[n % len(prefixes)]} {town}{suffix}",
            short_name=f"{town}{suffix}", abbreviation=abbreviation, city=town,
            color_primary=primary, color_secondary=secondary,
            stadium_name=f"Estádio Municipal de {town}",
            stadium_capacity=rng.randint(5000, 12000),
            founded_year=rng.randint(ref["founded_from"], ref["founded_to"]),
            reputation=int(ref["reputation"]), tier="small"))
        taken_ids.add(club_id)
        taken_abbr.add(abbreviation)
    return identities


# ---- 4. development ---------------------------------------------------------------------------


def _shift_attributes(player: Player, delta_ca: float, rng: random.Random) -> Player:
    """Move the player's visible attributes so his derived CA moves by about delta_ca.
    Stochastic rounding keeps small changes unbiased."""
    names = _VISIBLE_KEEPER if is_goalkeeper(player) else _VISIBLE_OUTFIELD
    shift = delta_ca * CA_TO_ATTRIBUTE
    values = {}
    for name in names:
        whole = math.floor(shift)
        step = whole + (1 if rng.random() < shift - whole else 0)
        values[name] = max(1, min(20, player.attributes.get(name) + step))
    attributes = dataclasses.replace(player.attributes, **values)
    moved = dataclasses.replace(player, attributes=attributes)
    ca = current_ability(moved)
    return dataclasses.replace(moved, potential_ability=max(moved.potential_ability, ca))


def develop(player: Player, age: int, rng: random.Random) -> Player:
    ref = _reference("development.toml")
    mean = _band(ref["bands"], age, "mean")
    delta = rng.gauss(mean, float(ref["sigma"]))
    ca = current_ability(player)
    if delta > 0:
        delta = min(delta, max(0, player.potential_ability - ca))
    return _shift_attributes(player, delta, rng) if delta else player


# ---- 5. retirement ----------------------------------------------------------------------------


def retirement_probability(player: Player, age: int, declined: bool) -> float:
    ref = _reference("retirement.toml")
    if age < ref["min_age"]:
        return 0.0
    p = _band(ref["bands"], age, "base")
    if declined:
        p *= ref["decline_factor"]
    a = player.attributes
    drive = a.get("professionalism") + a.get("ambition") - 20
    p *= min(ref["personality_max"],
             max(ref["personality_min"],
                 ref["personality_start"] - ref["personality_slope"] * drive))
    return float(min(ref["max_probability"], p))


# ---- 6. refill --------------------------------------------------------------------------------


def _quality(club: Club) -> float:
    if club.reputation >= 13:
        return TIER_QUALITY["strong"]
    if club.reputation >= 9:
        return TIER_QUALITY["mid"]
    return TIER_QUALITY["small"]


def _missing_positions(players: list[Player]) -> list[Position]:
    have = Counter(best_position(p) for p in players)
    need = Counter(SQUAD_SHAPE)
    missing: list[Position] = []
    for position in SQUAD_SHAPE:  # fixed order
        if need[position] > have[position]:
            missing.append(position)
            have[position] += 1
    while len(players) + len(missing) < SQUAD_SIZE:
        missing.append(Position.MC)
    return missing[: max(0, SQUAD_SIZE - len(players))]


def _free_number(taken: set[int]) -> int:
    return next(n for n in range(13, 100) if n not in taken)


# ---- the rollover -----------------------------------------------------------------------------


def next_season(career: Career) -> None:
    season = career.season
    outcome = season.outcome()
    assert outcome is not None, "the season is not finished"
    world = career.world
    generation = len(career.history)
    new_ref = world.reference_date.replace(year=world.reference_date.year + 1)

    clubs = dict(world.clubs)
    players = dict(world.players)
    memberships = dict(world.memberships)
    next_id = max(int(pid.split("-")[1]) for pid in players) + 1

    def new_pid() -> str:
        nonlocal next_id
        pid = f"p-{next_id:06d}"
        next_id += 1
        return pid

    # 2. promotion and relegation
    promoted = promoted_identities(world, generation)
    rng = _rng(career, "promoted")
    for identity in promoted:
        clubs[identity.id] = make_club(identity)
        squad = [(position, make_player(rng, new_pid(), position, TIER_QUALITY["small"],
                                        reference_date=new_ref))
                 for position in SQUAD_SHAPE]
        for (_, player), number in zip(squad, assign_shirt_numbers(squad), strict=True):
            players[player.id] = player
            memberships[player.id] = SquadMembership(player.id, identity.id, number)
    promoted_ids = tuple(i.id for i in promoted)
    participants = sorted((set(season.participants) - set(outcome.relegated))
                          | set(promoted_ids))

    # 3-5. ageing, development, retirement (promoted squads are brand new: not developed)
    dev_rng, ret_rng = _rng(career, "development"), _rng(career, "retirement")
    for pid in sorted(players):
        membership = memberships.get(pid)
        if membership is not None and membership.club_id in promoted_ids:
            continue
        player = players[pid]
        age = player.age(new_ref)
        before = current_ability(player)
        player = develop(player, age, dev_rng)
        players[pid] = player
        declined = current_ability(player) < before
        if ret_rng.random() < retirement_probability(player, age, declined):
            del players[pid]
            memberships.pop(pid, None)

    # 6. refill the participating squads with youngsters
    youth_rng = _rng(career, "youth")
    for club_id in participants:
        current = sorted((players[m.player_id] for m in memberships.values()
                          if m.club_id == club_id), key=lambda p: p.id)
        taken = {m.shirt_number for m in memberships.values()
                 if m.club_id == club_id and m.shirt_number is not None}
        for position in _missing_positions(current):
            age = youth_rng.randint(*YOUTH_AGES)
            youngster = make_player(youth_rng, new_pid(), position, _quality(clubs[club_id]),
                                    reference_date=new_ref, age=age)
            number = _free_number(taken)
            taken.add(number)
            players[youngster.id] = youngster
            memberships[youngster.id] = SquadMembership(youngster.id, club_id, number)

    # 1 + 7. history and the next season
    career.history.append(season_record(career, promoted_ids))
    world = dataclasses.replace(world, reference_date=new_ref, clubs=clubs, players=players,
                                memberships=memberships, record_flags=())
    career.world = world
    career.season = build_season(world, career.ruleset_toml, season.year + 1,
                                 career.master_seed, participants)
    career.current_date = career.season.current_date
    career.last_autosave = career.current_date
    career.pending = None
