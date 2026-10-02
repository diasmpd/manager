"""Derived Current Ability (research R8). CA is never stored, so it cannot contradict the
attributes. It is a rough mapping onto FM's 1-200 scale, re-calibrated in spec 011.

S = max over natural positions p of [0.85 * base(p) + 0.15 * mean(relevant visible attrs for p)]
CA = round(1 + (S - 1) * 199 / 19), clamped to 1-200.

Taking the max over per-position scores keeps CA monotonic: raising any attribute never lowers
it, even when it changes which position is best.
"""

from __future__ import annotations

from manager_core.domain.attributes import ATTRIBUTE_GROUPS, AttributeGroup
from manager_core.domain.player import Player
from manager_core.domain.positions import Position
from manager_core.ratings.suitability import base, suitability_milli

KEY_SHARE = 0.85
GENERAL_SHARE = 0.15

_OUTFIELD_GENERAL = (
    ATTRIBUTE_GROUPS[AttributeGroup.TECHNICAL]
    + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
    + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL]
)
_GK_GENERAL = (
    ATTRIBUTE_GROUPS[AttributeGroup.GOALKEEPING]
    + ATTRIBUTE_GROUPS[AttributeGroup.MENTAL]
    + ATTRIBUTE_GROUPS[AttributeGroup.PHYSICAL]
)


def _general(player: Player, position: Position) -> float:
    names = _GK_GENERAL if position is Position.GK else _OUTFIELD_GENERAL
    return sum(player.attributes.get(n) for n in names) / len(names)


def _score(player: Player, position: Position) -> float:
    return KEY_SHARE * base(player, position) + GENERAL_SHARE * _general(player, position)


def current_ability(player: Player) -> int:
    s = max(_score(player, p) for p in player.positions.natural_positions())
    return max(1, min(200, round(1 + (s - 1) * 199 / 19)))


def best_position(player: Player) -> Position:
    """Highest suitability (familiarity included) among positions with familiarity >= 15.

    Integer milli-points make ties exact; ties go to the earlier FM position. Using suitability
    rather than the raw base matters for mirrored positions (AML/AMR share weights): a natural
    AMR who is only accomplished at AML is an AMR.
    """
    naturals = player.positions.natural_positions()  # already in FM order
    return max(naturals, key=lambda p: (suitability_milli(player, p), -p.order))


def is_goalkeeper(player: Player) -> bool:
    return best_position(player) is Position.GK
