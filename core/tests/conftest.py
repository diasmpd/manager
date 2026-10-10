import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from manager_core.career import career as career_mod
from manager_core.career import store
from manager_core.career.career import Career

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _user_matches_on_the_quick_sim(request: pytest.FixtureRequest,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """Careers made or loaded in a test play the user's matches on the quick sim, as they did
    before spec 008. A positional match costs seconds, and most career tests are about the day
    loop, the save or the rules: on the positional engine one career season takes about 50 s.
    A test about the user's matches themselves asks for them with `@pytest.mark.positional`."""
    if request.node.get_closest_marker("positional") is not None:
        return

    def quick(make: Callable[..., Career]) -> Callable[..., Career]:
        def made(*args: Any, **kwargs: Any) -> Career:
            career = make(*args, **kwargs)
            career.positional = False
            return career

        return made

    monkeypatch.setattr(career_mod, "new_career", quick(career_mod.new_career))
    monkeypatch.setattr(store, "load", quick(store.load))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def sample_dir() -> Path:
    return REPO_ROOT / "data" / "sample"


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def tmp_dataset(tmp_path: Path) -> Callable[[Path], Path]:
    """Copy a dataset folder into a temp dir so a test can modify it safely."""

    def _copy(src: Path) -> Path:
        dst = tmp_path / src.name
        shutil.copytree(src, dst)
        return dst

    return _copy
