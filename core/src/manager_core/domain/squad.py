"""Squad membership: links a player to a club (data-model.md "SquadMembership")."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SquadMembership:
    player_id: str
    club_id: str
    shirt_number: int | None = None
    market_value: int | None = None
    wage_monthly: int | None = None
    currency: str | None = None
    contract_expiry: date | None = None

    def __post_init__(self) -> None:
        if self.shirt_number is not None and not 1 <= self.shirt_number <= 99:
            raise ValueError(f"shirt number out of range: {self.shirt_number}")
        money = (self.market_value, self.wage_monthly)
        if any(m is not None and m < 0 for m in money):
            raise ValueError("money fields must be >= 0")
        if any(m is not None for m in money) and not self.currency:
            raise ValueError("currency is required when a money field is set")
