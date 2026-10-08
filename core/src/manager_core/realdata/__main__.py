"""The real-data CLI (spec 011, contracts/realdata-cli.md).

    python -m manager_core.realdata collect --data-repo ..\\manager-data [--refresh] [--delay 4]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from manager_core.realdata.fetch import DEFAULT_DELAY, Fetcher, SourceStopped
from manager_core.realdata.sources import ogol

PUBLIC_REPO = Path(__file__).resolve().parents[4]


def _inside_public(path: Path) -> bool:
    try:
        path.resolve().relative_to(PUBLIC_REPO)
    except ValueError:
        return False
    return True


def _inputs(data_repo: Path) -> dict:  # type: ignore[type-arg]
    return tomllib.loads((data_repo / "inputs" / "mineiro.toml").read_text("utf-8"))


def collect(data_repo: Path, refresh: bool, delay: float) -> int:
    """Club pages, then every rostered player's page, through the polite cached fetcher."""
    inputs = _inputs(data_repo)
    season = int(inputs["ogol_season"])
    fetcher = Fetcher(data_repo / "cache" / "ogol", delay=delay, refresh=refresh)
    try:
        for club in inputs["clubs"]:
            page = fetcher.get(f"{ogol.BASE}{club['ogol']}?epoca_id={season}")
            roster = ogol.parse_club(page).squad
            print(f"{club['club_id']}: {len(roster)} players", flush=True)
            for entry in roster:
                fetcher.get(f"{ogol.BASE}/jogador/{entry.slug}/{entry.ogol_id}?epoca_id={season}")
            print(f"  fetched {fetcher.fetched}, from cache {fetcher.cached}", flush=True)
    except SourceStopped as stop:
        print(f"stopped: {stop}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m manager_core.realdata")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("collect")
    cmd.add_argument("--data-repo", type=Path, required=True)
    cmd.add_argument("--refresh", action="store_true")
    cmd.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    args = parser.parse_args(argv)
    if _inside_public(args.data_repo):
        print("refused: the data repository must not be inside the public repository",
              file=sys.stderr)
        return 1
    if args.command == "collect":
        return collect(args.data_repo, args.refresh, max(args.delay, DEFAULT_DELAY))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
