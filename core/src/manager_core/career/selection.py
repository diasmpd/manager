"""The user's team selection (spec 005 FR-003/FR-004, research R2).

The assistant proposes the best XI for a formation (001's exact best XI, without suspended
players); the owner edits it; the confirmed selection is played as is. All rules live here, so
every client (terminal UI, CLI, later Godot) shares them (Constitution III).
"""

from __future__ import annotations

from dataclasses import dataclass

from manager_core.career.career import Career
from manager_core.career.discipline import Discipline
from manager_core.domain.formation import load_catalogue
from manager_core.domain.positions import Position
from manager_core.quicksim.squad import BENCH_SIZE, NO_GOALKEEPER, TeamSheet, build_team_sheet
from manager_core.ratings.ability import is_goalkeeper

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Selection:
    formation: str
    starters: tuple[tuple[int, str], ...]  # (slot index, player id)
    bench: tuple[str, ...]

    @property
    def players(self) -> tuple[str, ...]:
        return tuple(pid for _, pid in self.starters) + self.bench


@dataclass(frozen=True, slots=True)
class SelectionIssue:
    code: str  # unknown_formation / slots / not_in_squad / duplicate / suspended /
    #            bench_too_long / no_goalkeeper
    severity: str  # error / warning
    player_id: str | None = None


def _suspended(career: Career) -> frozenset[str]:
    ledger = career.season.discipline
    if isinstance(ledger, Discipline):
        return ledger.suspended(career.user_club_id)
    return frozenset()


def _squad_ids(career: Career) -> set[str]:
    return {m.player_id for m in career.world.memberships.values()
            if m.club_id == career.user_club_id}


def propose(career: Career, formation: str = "4-4-2") -> Selection:
    """The assistant's XI and bench for the formation, without suspended players."""
    out = _suspended(career)
    squad = sorted((p for p in career.world.squad(career.user_club_id) if p.id not in out),
                   key=lambda p: p.id)
    sheet = build_team_sheet(career.user_club_id, squad, formation)
    return Selection(formation, tuple(sorted(sheet.starters)), sheet.bench)


def validate(career: Career, selection: Selection) -> list[SelectionIssue]:
    issues: list[SelectionIssue] = []
    catalogue = load_catalogue()
    if selection.formation not in catalogue:
        return [SelectionIssue("unknown_formation", ERROR)]
    formation = catalogue[selection.formation]
    slots = [i for i, _ in selection.starters]
    if sorted(set(slots)) != slots or not all(0 <= i < len(formation.slots) for i in slots):
        issues.append(SelectionIssue("slots", ERROR))
    squad = _squad_ids(career)
    seen: set[str] = set()
    for pid in selection.players:
        if pid not in squad:
            issues.append(SelectionIssue("not_in_squad", ERROR, pid))
        if pid in seen:
            issues.append(SelectionIssue("duplicate", ERROR, pid))
        seen.add(pid)
    for pid in sorted(set(selection.players) & _suspended(career)):
        issues.append(SelectionIssue("suspended", ERROR, pid))
    if len(selection.bench) > BENCH_SIZE:
        issues.append(SelectionIssue("bench_too_long", ERROR))
    if not any(i.severity == ERROR for i in issues):
        keeper = next((pid for i, pid in selection.starters
                       if formation.slots[i].position is Position.GK), None)
        if keeper is None or not is_goalkeeper(career.world.player(keeper)):
            issues.append(SelectionIssue(NO_GOALKEEPER, WARNING, keeper))
    return issues


def to_team_sheet(career: Career, selection: Selection) -> TeamSheet:
    formation = load_catalogue()[selection.formation]
    flags = tuple(i.code for i in validate(career, selection) if i.code == NO_GOALKEEPER)
    return TeamSheet(career.user_club_id, formation, tuple(sorted(selection.starters)),
                     selection.bench, flags)
