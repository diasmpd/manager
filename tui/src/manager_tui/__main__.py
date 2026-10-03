"""`python -m manager_tui [--saves DIR] [CAREER]` (spec 005 FR-011)."""

from __future__ import annotations

import argparse
from pathlib import Path

from manager_tui.app import ManagerApp, default_saves


def main() -> None:
    parser = argparse.ArgumentParser(prog="manager_tui")
    parser.add_argument("career", nargs="?")
    parser.add_argument("--saves", type=Path, default=default_saves())
    args = parser.parse_args()
    ManagerApp(args.saves, args.career).run()


if __name__ == "__main__":
    main()
