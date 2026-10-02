import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


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
