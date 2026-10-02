"""Formations and team instructions, modelled on Football Manager's tactics screen.

Coordinates are in metres on a 105 x 68 pitch, in the team's own frame:
x = 0 is the team's own goal line, x = 105 the opponent's; y = 0 is the left touchline.
Slot coordinates are the player's base position when the ball is around the halfway line;
the engine shifts the whole block with the ball.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0


@dataclass(frozen=True)
class Slot:
    position: str   # FM position code (GK, DC, MC, ST, ...)
    x: float
    y: float


FORMATIONS: dict[str, list[Slot]] = {
    "4-4-2": [
        Slot("GK", 5, 34),
        Slot("DL", 30, 8), Slot("DC", 26, 25), Slot("DC", 26, 43), Slot("DR", 30, 60),
        Slot("ML", 52, 9), Slot("MC", 48, 27), Slot("MC", 48, 41), Slot("MR", 52, 59),
        Slot("ST", 70, 28), Slot("ST", 70, 40),
    ],
    "4-3-3": [
        Slot("GK", 5, 34),
        Slot("DL", 30, 8), Slot("DC", 26, 25), Slot("DC", 26, 43), Slot("DR", 30, 60),
        Slot("DM", 40, 34), Slot("MC", 50, 24), Slot("MC", 50, 44),
        Slot("AML", 66, 10), Slot("ST", 72, 34), Slot("AMR", 66, 58),
    ],
    "4-2-3-1": [
        Slot("GK", 5, 34),
        Slot("DL", 30, 8), Slot("DC", 26, 25), Slot("DC", 26, 43), Slot("DR", 30, 60),
        Slot("DM", 40, 27), Slot("DM", 40, 41),
        Slot("AML", 60, 10), Slot("AMC", 60, 34), Slot("AMR", 60, 58),
        Slot("ST", 72, 34),
    ],
    "3-5-2": [
        Slot("GK", 5, 34),
        Slot("DC", 26, 20), Slot("DC", 24, 34), Slot("DC", 26, 48),
        Slot("WBL", 44, 6), Slot("DM", 40, 34), Slot("MC", 50, 24), Slot("MC", 50, 44), Slot("WBR", 44, 62),
        Slot("ST", 70, 28), Slot("ST", 70, 40),
    ],
    "5-3-2": [
        Slot("GK", 5, 34),
        Slot("WBL", 30, 6), Slot("DC", 24, 20), Slot("DC", 22, 34), Slot("DC", 24, 48), Slot("WBR", 30, 62),
        Slot("MC", 46, 22), Slot("MC", 44, 34), Slot("MC", 46, 46),
        Slot("ST", 68, 28), Slot("ST", 68, 40),
    ],
}


class Mentality(IntEnum):
    VERY_DEFENSIVE = -2
    DEFENSIVE = -1
    BALANCED = 0
    POSITIVE = 1
    VERY_ATTACKING = 2


class Level(IntEnum):
    """Generic 3-step instruction (lower / standard / higher), as FM's sliders."""
    LOW = -1
    NORMAL = 0
    HIGH = 1


@dataclass
class TeamInstructions:
    mentality: Mentality = Mentality.BALANCED
    tempo: Level = Level.NORMAL              # how quickly the team moves the ball
    width: Level = Level.NORMAL              # how wide the team plays in possession
    directness: Level = Level.NORMAL         # short passing (LOW) ... direct/long balls (HIGH)
    pressing: Level = Level.NORMAL           # pressing intensity
    line_of_engagement: Level = Level.NORMAL  # where pressing starts
    defensive_line: Level = Level.NORMAL     # how high the back line holds
    tackling: Level = Level.NORMAL           # ease off (LOW) / stay on feet / get stuck in (HIGH)
    offside_trap: bool = False
    # Booked players automatically ease off their tackles to avoid a second yellow.
    card_caution: bool = True


@dataclass
class Tactic:
    formation: str = "4-4-2"
    instructions: TeamInstructions = field(default_factory=TeamInstructions)

    @property
    def slots(self) -> list[Slot]:
        return FORMATIONS[self.formation]
