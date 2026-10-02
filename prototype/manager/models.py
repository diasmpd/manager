"""Core data model, following Football Manager's attribute set (1-20 scale).

Visible attributes are grouped as in FM (technical / mental / physical / goalkeeping).
Hidden attributes (consistency, temperament, ...) exist in FM too: the player
never sees them directly, but they shape behaviour in matches.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

TECHNICAL = ["corners", "crossing", "dribbling", "finishing", "first_touch", "free_kicks", "heading",
             "long_shots", "marking", "passing", "penalty_taking", "tackling", "technique"]
MENTAL = ["aggression", "anticipation", "bravery", "composure", "concentration", "decisions", "determination",
          "flair", "leadership", "off_the_ball", "positioning", "teamwork", "vision", "work_rate"]
PHYSICAL = ["acceleration", "agility", "balance", "jumping_reach", "natural_fitness", "pace", "stamina", "strength"]
GOALKEEPING = ["aerial_reach", "command_of_area", "handling", "kicking", "one_on_ones", "reflexes", "rushing_out"]
HIDDEN = ["consistency", "dirtiness", "important_matches", "injury_proneness", "temperament"]


@dataclass
class Attributes:
    # technical
    corners: int = 10
    crossing: int = 10
    dribbling: int = 10
    finishing: int = 10
    first_touch: int = 10
    free_kicks: int = 10
    heading: int = 10
    long_shots: int = 10
    marking: int = 10
    passing: int = 10
    penalty_taking: int = 10
    tackling: int = 10
    technique: int = 10
    # mental
    aggression: int = 10
    anticipation: int = 10
    bravery: int = 10
    composure: int = 10
    concentration: int = 10
    decisions: int = 10
    determination: int = 10
    flair: int = 10
    leadership: int = 10
    off_the_ball: int = 10
    positioning: int = 10
    teamwork: int = 10
    vision: int = 10
    work_rate: int = 10
    # physical
    acceleration: int = 10
    agility: int = 10
    balance: int = 10
    jumping_reach: int = 10
    natural_fitness: int = 10
    pace: int = 10
    stamina: int = 10
    strength: int = 10
    # goalkeeping (outfield players keep these low)
    aerial_reach: int = 1
    command_of_area: int = 1
    handling: int = 1
    kicking: int = 1
    one_on_ones: int = 1
    reflexes: int = 1
    rushing_out: int = 1
    # hidden
    consistency: int = 10       # match-to-match variance
    dirtiness: int = 8          # willingness to commit cynical fouls
    important_matches: int = 10
    injury_proneness: int = 8
    temperament: int = 10       # self-control under provocation: drives reaction to a booking

    @classmethod
    def names(cls) -> list[str]:
        return [f.name for f in fields(cls)]


# Position codes as in FM. Each player has a familiarity (1-20) per position he can play.
POSITIONS = ["GK", "DL", "DC", "DR", "WBL", "WBR", "DM", "ML", "MC", "MR", "AML", "AMC", "AMR", "ST"]


@dataclass
class Player:
    name: str
    positions: dict[str, int]          # e.g. {"DC": 20, "DM": 12}
    attrs: Attributes = field(default_factory=Attributes)
    age: int = 25
    nationality: str = "Brasil"

    @property
    def main_position(self) -> str:
        return max(self.positions, key=self.positions.get)

    def familiarity(self, position: str) -> int:
        return self.positions.get(position, 1)

    @property
    def is_goalkeeper(self) -> bool:
        return self.main_position == "GK"

    def __getattr__(self, item):
        # player.finishing -> player.attrs.finishing (keeps engine code readable)
        if item != "attrs" and item in Attributes.__dataclass_fields__:
            return getattr(self.attrs, item)
        raise AttributeError(item)


# Key attributes per position, used to rate how good a player is in a slot (FM's "role suitability").
POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "GK": {"reflexes": 3, "handling": 2, "one_on_ones": 2, "aerial_reach": 1.5, "command_of_area": 1.5,
           "positioning": 1.5, "concentration": 1, "kicking": 0.5, "rushing_out": 0.5},
    "DC": {"tackling": 2, "marking": 2, "positioning": 2, "heading": 1.5, "jumping_reach": 1.5, "strength": 1,
           "anticipation": 1, "concentration": 1, "pace": 0.5, "decisions": 0.5},
    "DL": {"tackling": 1.5, "marking": 1.5, "positioning": 1.5, "pace": 1.5, "stamina": 1, "crossing": 1,
           "acceleration": 1, "work_rate": 1, "passing": 0.5},
    "WBL": {"crossing": 1.5, "pace": 1.5, "stamina": 1.5, "work_rate": 1, "dribbling": 1, "tackling": 1,
            "acceleration": 1, "off_the_ball": 0.5, "passing": 0.5},
    "DM": {"tackling": 1.5, "positioning": 1.5, "passing": 1.5, "anticipation": 1, "decisions": 1,
           "teamwork": 1, "work_rate": 1, "marking": 1, "concentration": 0.5},
    "MC": {"passing": 2, "vision": 1.5, "decisions": 1.5, "first_touch": 1, "technique": 1, "teamwork": 1,
           "work_rate": 1, "stamina": 1, "tackling": 0.5, "off_the_ball": 0.5},
    "ML": {"crossing": 1.5, "dribbling": 1.5, "pace": 1.5, "acceleration": 1, "passing": 1, "technique": 1,
           "work_rate": 1, "stamina": 1, "off_the_ball": 0.5},
    "AMC": {"passing": 1.5, "vision": 1.5, "technique": 1.5, "dribbling": 1, "flair": 1, "first_touch": 1,
            "decisions": 1, "off_the_ball": 1, "long_shots": 0.5, "finishing": 0.5},
    "AML": {"dribbling": 2, "pace": 1.5, "acceleration": 1.5, "technique": 1, "crossing": 1, "flair": 1,
            "off_the_ball": 1, "finishing": 0.5, "agility": 0.5},
    "ST": {"finishing": 2.5, "off_the_ball": 1.5, "composure": 1.5, "first_touch": 1, "pace": 1,
           "acceleration": 1, "heading": 1, "anticipation": 1, "strength": 0.5, "dribbling": 0.5},
}
for _left, _right in (("DL", "DR"), ("WBL", "WBR"), ("ML", "MR"), ("AML", "AMR")):
    POSITION_WEIGHTS[_right] = POSITION_WEIGHTS[_left]


def position_ability(player: Player, position: str) -> float:
    """Weighted attribute average for that position (1-20), reduced when the player is unfamiliar with it."""
    weights = POSITION_WEIGHTS[position]
    base = sum(getattr(player.attrs, a) * w for a, w in weights.items()) / sum(weights.values())
    fam = player.familiarity(position)
    return base * (0.55 + 0.45 * fam / 20)


@dataclass
class Team:
    name: str
    squad: list[Player]
    tactic: "Tactic" = None
    lineup: list[Player] | None = None   # aligned with tactic.slots; None = pick best XI automatically
    bench: list[Player] | None = None
    reputation: int = 10                  # 1-20, used later for finances/board/media

    def __post_init__(self):
        from .tactics import Tactic
        if self.tactic is None:
            self.tactic = Tactic()
        if self.lineup is None:
            self.lineup = self.pick_best_xi()
        if self.bench is None:
            chosen = {id(p) for p in self.lineup}
            rest = [p for p in self.squad if id(p) not in chosen]
            self.bench = self._pick_bench(rest)

    def pick_best_xi(self) -> list[Player]:
        """Greedy assignment: fill the most demanding slots first with the best available player."""
        slots = self.tactic.slots
        available = list(self.squad)
        lineup: list[Player | None] = [None] * len(slots)
        order = sorted(range(len(slots)), key=lambda i: slots[i].position != "GK")
        for i in order:
            best = max(available, key=lambda p: position_ability(p, slots[i].position))
            lineup[i] = best
            available.remove(best)
        return lineup

    @staticmethod
    def _pick_bench(rest: list[Player], size: int = 9) -> list[Player]:
        rest = sorted(rest, key=lambda p: position_ability(p, p.main_position), reverse=True)
        bench = [p for p in rest if p.is_goalkeeper][:1]
        bench += [p for p in rest if not p.is_goalkeeper][: size - len(bench)]
        return bench
