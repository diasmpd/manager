"""The dev tools' own promises (core/tools)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2]
BELOW_NORMAL = 0x4000
PRIORITY_OF_THIS_PROCESS = (
    "import ctypes; k = ctypes.WinDLL('kernel32'); "
    "k.GetCurrentProcess.restype = ctypes.c_void_p; "
    "k.GetPriorityClass.argtypes = (ctypes.c_void_p,); "
    "print(k.GetPriorityClass(k.GetCurrentProcess()))"
)


@pytest.mark.skipif(os.name != "nt", reason="the Windows priority class")
def test_the_tuner_low_priority_really_lowers_the_process() -> None:
    """Regression: `--low-priority` failed without a word (a truncated 64-bit handle), so long
    tuner runs took the whole PC at normal priority."""
    code = ("from tools.tune_positional import _lower_priority; _lower_priority(); "
            + PRIORITY_OF_THIS_PROCESS)
    done = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True,
                          check=True)
    assert int(done.stdout) == BELOW_NORMAL
