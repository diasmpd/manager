"""The public-repository guard (spec 011 R7, SC-006): real data must never be committed here.

Checks the tracked files of the repository for the private repository's layout and for any
dataset that is not declared fictional.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PRIVATE_NAMES = ("corrections.csv", "import-report.md")
PRIVATE_DIRS = ("cache/", "datasets/", "inputs/")


def tracked_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True,
                         check=True)
    return out.stdout.splitlines()


def violations(repo: Path) -> list[str]:
    problems: list[str] = []
    for name in tracked_files(repo):
        posix = name.replace("\\", "/")
        if posix.endswith(PRIVATE_NAMES) or any(posix.startswith(d) or f"/{d}" in posix
                                                for d in PRIVATE_DIRS):
            problems.append(f"{name}: private layout (real data never goes in the public repo)")
        if posix.endswith("dataset.csv"):
            text = (repo / name).read_text("utf-8-sig", errors="replace")
            header, _, row = text.partition("\n")
            values = row.split(";")
            fields = header.split(";")
            if "fictional" not in fields or values[fields.index("fictional")].strip() != "true":
                problems.append(f"{name}: dataset is not declared fictional")
    return problems
