"""Suspensions (spec 004 FR-008..FR-010, research R5; owner decision: real rules).

The ledger is derived from match reports as the season is played (or replayed from a save), so
it is never stored and cannot disagree with the results:
- a red card (direct, or a second yellow) bans the player from his club's next match;
- a third yellow card bans him from the next match and resets his count;
- a yellow that became a second-yellow red counts toward the red only.
A new season starts with an empty ledger.
"""

from __future__ import annotations

from typing import Any

from manager_core.competition.season import Match
from manager_core.domain.dataset import Dataset

YELLOWS_PER_BAN = 3
SENT_OFF = ("red", "second_yellow")


class Discipline:
    def __init__(self, world: Dataset) -> None:
        self._club_of = {pid: m.club_id for pid, m in world.memberships.items()}
        self._yellows: dict[str, int] = {}
        self._bans: dict[str, int] = {}

    def yellows(self, player_id: str) -> int:
        return self._yellows.get(player_id, 0)

    def bans(self, player_id: str) -> int:
        return self._bans.get(player_id, 0)

    def suspended(self, club_id: str) -> frozenset[str]:
        return frozenset(pid for pid, n in self._bans.items()
                         if n > 0 and self._club_of.get(pid) == club_id)

    def unavailable(self, match: Match) -> frozenset[str]:
        return self.suspended(match.home_id) | self.suspended(match.away_id)

    def record(self, match: Match, result: Any) -> None:
        # bans owed before this match were served by it
        for club in (match.home_id, match.away_id):
            for pid in self.suspended(club):
                self._bans[pid] -= 1
        report = getattr(result, "report", None)
        if report is None:
            return
        sent = {e.player_id for e in report.events if e.kind in SENT_OFF}
        for e in report.events:
            if e.kind == "yellow" and e.player_id not in sent:
                count = self._yellows.get(e.player_id, 0) + 1
                if count == YELLOWS_PER_BAN:
                    count = 0
                    self._bans[e.player_id] = self._bans.get(e.player_id, 0) + 1
                self._yellows[e.player_id] = count
        for pid in sorted(sent):
            self._bans[pid] = self._bans.get(pid, 0) + 1
