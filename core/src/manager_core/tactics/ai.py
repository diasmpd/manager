"""AI clubs' tactics: a style per club, adapted per match and late in the match (spec 006 FR-009,
research R5).

- `assign_styles` scores each style from the club's squad traits (standardised across the world)
  plus a seeded manager preference, and picks the best. Deterministic.
- `style_tactic` turns a style into a full tactic for the club's formation.
- `pre_match` adapts it to the opponent's strength and the venue.
- `in_match_mentality` steps the mentality late in the match by the score.
"""

from __future__ import annotations

import dataclasses
import statistics
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from manager_core.competition.seeds import sub_seed
from manager_core.domain.player import Player
from manager_core.quicksim.ratings import POSITION_GROUP, Group, rate
from manager_core.quicksim.squad import TeamSheet
from manager_core.tactics.catalogue import load_options
from manager_core.tactics.model import Tactic, default_tactic

FEATURES = ("attack", "control", "defence", "pace", "energy", "aerial", "reputation")
MANAGER_SEED = 6006  # the manager profiles of M0 are fixed per club (no staff model yet)


@cache
def styles_table() -> dict[str, Any]:
    entry = resources.files("manager_core.reference").joinpath("tactics").joinpath("styles.toml")
    return tomllib.loads(entry.read_text("utf-8"))


def style_ids() -> tuple[str, ...]:
    return tuple(styles_table()["styles"])


@dataclass(frozen=True, slots=True)
class SquadProfile:
    attack: float
    control: float
    defence: float
    pace: float
    energy: float
    aerial: float
    reputation: float

    def get(self, name: str) -> float:
        return float(getattr(self, name))


def _mean(players: list[Player], names: tuple[str, ...]) -> float:
    if not players:
        return 10.0
    return statistics.fmean(p.attributes.get(n) for p in players for n in names)


def squad_profile(sheet: TeamSheet, players: Mapping[str, Player], reputation: int) -> SquadProfile:
    on = [(sheet.slot_position(i), players[pid]) for i, pid in sheet.starters]
    ratings = rate(on, [s.position for s in sheet.formation.slots])
    front = [p for pos, p in on
             if POSITION_GROUP[pos] in (Group.ATTACKING_MID, Group.FORWARD)]
    strikers = [p for pos, p in on if POSITION_GROUP[pos] is Group.FORWARD] or front
    outfield = [p for pos, p in on if POSITION_GROUP[pos] is not Group.GOALKEEPER]
    return SquadProfile(
        attack=ratings.attack, control=ratings.control, defence=ratings.defence,
        pace=_mean(front, ("pace", "acceleration")),
        energy=_mean(outfield, ("work_rate", "stamina", "aggression")),
        aerial=_mean(strikers, ("heading", "jumping_reach", "strength")),
        reputation=float(reputation))


def strength(sheet: TeamSheet, players: Mapping[str, Player]) -> float:
    """One number for pre-match comparisons: the mean of the XI's four main ratings."""
    on = [(sheet.slot_position(i), players[pid]) for i, pid in sheet.starters]
    r = rate(on, [s.position for s in sheet.formation.slots])
    return (r.attack + r.control + r.defence + r.goalkeeping) / 4


def manager_preference(club_id: str) -> dict[str, float]:
    """A fixed preference in [0, manager_weight) per style for this club's manager."""
    weight = float(styles_table()["manager_weight"])
    out = {}
    for style in style_ids():
        draw = sub_seed(MANAGER_SEED, f"manager:{club_id}:{style}") % 10_000 / 10_000
        out[style] = weight * draw
    return out


def assign_styles(profiles: Mapping[str, SquadProfile]) -> dict[str, str]:
    """club id -> style id. A squad trait is the feature relative to the club's own level (pace
    above the squad's standard, say), scored as a z-score across `profiles`; reputation is
    absolute (big clubs prefer the ball)."""
    traits = {cid: _traits(p) for cid, p in profiles.items()}
    stats = {}
    for name in FEATURES:
        values = [t[name] for t in traits.values()]
        mean = statistics.fmean(values)
        spread = statistics.pstdev(values) or 1.0
        stats[name] = (mean, spread)
    styles = styles_table()["styles"]
    out = {}
    for club_id in sorted(profiles):
        profile = traits[club_id]
        prefs = manager_preference(club_id)
        scores = {}
        for style, spec in styles.items():
            score = prefs[style]
            for trait, weight in spec["traits"].items():
                if trait == "bias":
                    score += weight
                else:
                    mean, spread = stats[trait]
                    score += weight * (profile[trait] - mean) / spread
            scores[style] = score
        out[club_id] = max(sorted(scores), key=lambda s: scores[s])
    return out


def _traits(profile: SquadProfile) -> dict[str, float]:
    level = (profile.attack + profile.control + profile.defence) / 3
    return {name: profile.get(name) - (0.0 if name == "reputation" else level)
            for name in FEATURES}


def style_tactic(style: str, ip_formation: str) -> Tactic:
    spec = styles_table()["styles"][style]
    base = default_tactic(ip_formation, style=style)
    team = dict(base.team)
    team.update(spec["team"])
    return dataclasses.replace(base, mentality=spec["mentality"],
                               team=tuple(sorted(team.items())))


def _step(mentality: str, steps: int) -> str:
    settings = load_options().mentality.settings
    index = settings.index(mentality) + steps
    return settings[max(0, min(len(settings) - 1, index))]


def pre_match(tactic: Tactic, own: float, opponent: float, home: bool,
              neutral: bool = False) -> Tactic:
    """Adapt to the opponent and the venue: a big underdog away goes at most Cautious and no
    higher than a mid block; a big favourite at home goes one step more attacking. Both rules
    are about the venue, so nothing changes at a neutral ground."""
    if neutral:
        return tactic
    rules = styles_table()["adaptation"]
    ratio = own / max(1.0, opponent)
    settings = load_options().mentality.settings
    if ratio < rules["big_underdog"] and not home:
        cap = rules["underdog_cap"]
        mentality = min(tactic.mentality, cap, key=settings.index)
        lines = load_options().team_option("line_of_engagement")
        assert lines is not None
        line = tactic.setting("line_of_engagement")
        deepest = max(line, rules["underdog_line"], key=lines.settings.index)
        team = dict(tactic.team)
        team["line_of_engagement"] = deepest
        if deepest != line and team.get("defensive_line") in ("higher", "much_higher"):
            team["defensive_line"] = "standard"
        return dataclasses.replace(tactic, mentality=mentality, team=tuple(sorted(team.items())))
    if ratio > rules["big_favourite"] and home:
        return dataclasses.replace(tactic, mentality=_step(tactic.mentality, 1))
    return tactic


def in_match_mentality(start: str, base_minute: int, goal_diff: int) -> str:
    """The AI's mentality at this minute, from its pre-match one and the score."""
    rules = styles_table()["adaptation"]
    if base_minute <= rules["late_minute"]:
        return start
    if goal_diff < 0:
        return _step(start, 2 if goal_diff <= -2 else 1)
    if goal_diff >= rules["protect_lead"]:
        return _step(start, -1)
    return start
