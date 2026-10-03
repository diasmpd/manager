"""Season seed and per-decision sub-seeds: SHA-256 based, stable across processes (research R4)."""

import hashlib

from manager_core.competition.seeds import season_seed, sub_seed


def _sha(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def test_season_seed_is_sha256_of_master_and_year() -> None:
    assert season_seed(20261002, 2027) == _sha("season:20261002:2027")


def test_season_seed_varies() -> None:
    base = season_seed(20261002, 2027)
    assert season_seed(20261002, 2028) != base
    assert season_seed(1, 2027) != base


def test_sub_seed_is_stable_and_label_sensitive() -> None:
    seed = season_seed(20261002, 2027)
    assert sub_seed(seed, "draw:mg") == _sha(f"{seed}:draw:mg")
    assert sub_seed(seed, "draw:mg") == sub_seed(seed, "draw:mg")
    assert sub_seed(seed, "match:a") != sub_seed(seed, "match:b")
