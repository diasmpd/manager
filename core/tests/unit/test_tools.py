"""The dev tools' own promises (core/tools)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2]
NORMAL, BELOW_NORMAL = 0x20, 0x4000
PRIORITY_OF_THIS_PROCESS = (
    "import ctypes; k = ctypes.WinDLL('kernel32'); "
    "k.GetCurrentProcess.restype = ctypes.c_void_p; "
    "k.GetPriorityClass.argtypes = (ctypes.c_void_p,); "
    "print(k.GetPriorityClass(k.GetCurrentProcess()))"
)


@pytest.mark.skipif(os.name != "nt", reason="the Windows priority class")
@pytest.mark.parametrize("lower", [
    "from tools.tune_positional import _lower_priority as lower",
    "from manager_core.calibration.positional import lower_priority as lower",
])
def test_low_priority_really_lowers_the_process(lower: str) -> None:
    """Regression: `--low-priority` failed without a word (a truncated 64-bit handle), so long
    tuner runs took the whole PC at normal priority. The process starts at normal priority
    whatever this test run's own is: a child of a low-priority run would inherit it and pass
    with nothing lowered."""
    code = f"{PRIORITY_OF_THIS_PROCESS}; {lower}; lower(); {PRIORITY_OF_THIS_PROCESS}"
    done = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True,
                          check=True, creationflags=subprocess.NORMAL_PRIORITY_CLASS)
    assert [int(line) for line in done.stdout.split()] == [NORMAL, BELOW_NORMAL]
