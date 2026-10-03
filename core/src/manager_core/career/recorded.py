"""`RecordedProvider`: stored results first, the live provider after (spec 004, research R1).

Loading a save replays the season with the results it stored, so a later change to the quick
sim never rewrites a career's past. Matches not yet played fall through to the live provider.
"""

from __future__ import annotations

import random
from collections.abc import Mapping

from manager_core.competition.results import MatchContext, Result, ResultProvider, Shootout
from manager_core.domain.club import Club


class RecordedProvider:
    def __init__(self, recorded: Mapping[str, Result], live: ResultProvider) -> None:
        self.recorded = dict(recorded)
        self.live = live
        self.used: set[str] = set()

    def play(self, match_id: str, home: Club, away: Club, context: MatchContext,
             rng: random.Random) -> Result:
        if match_id in self.recorded:
            self.used.add(match_id)
            return self.recorded[match_id]
        return self.live.play(match_id, home, away, context, rng)

    def shootout(self, match_id: str, first: Club, second: Club, context: MatchContext,
                 rng: random.Random, *, last_result: Result | None = None) -> Shootout:
        # a stored last leg already carries its shootout, so this only runs for live matches
        return self.live.shootout(match_id, first, second, context, rng,
                                  last_result=last_result)
