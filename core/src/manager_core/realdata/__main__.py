"""The real-data CLI (spec 011, contracts/realdata-cli.md).

    python -m manager_core.realdata collect --data-repo ..\\manager-data [--refresh] [--delay 4]
    python -m manager_core.realdata build --data-repo ..\\manager-data --out datasets\\mineiro-2026
    python -m manager_core.realdata strength --data-repo ..\\manager-data --out ... [--seasons 100]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import tomllib
from datetime import date
from pathlib import Path

from manager_core import api
from manager_core.realdata import corrections, strength
from manager_core.realdata.build import COMPETITIONS, build
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
    cmd = sub.add_parser("build")
    cmd.add_argument("--data-repo", type=Path, required=True)
    cmd.add_argument("--competition", choices=sorted(COMPETITIONS), default="mineiro-1")
    cmd.add_argument("--out", type=Path, required=True,
                     help="the dataset folder, relative to the data repository")
    cmd = sub.add_parser("correct", help="append an owner correction (R5)")
    cmd.add_argument("--data-repo", type=Path, required=True)
    cmd.add_argument("--record", required=True, help="player:p-og123 or club:cruzeiro")
    cmd.add_argument("--field", required=True)
    cmd.add_argument("--value", required=True)
    cmd.add_argument("--note", default="")
    cmd.add_argument("--out", type=Path, default=Path("datasets") / "mineiro-2026",
                     help="the built dataset the current value is read from")
    cmd = sub.add_parser("strength", help="SC-003: simulated title shares against the real ones")
    cmd.add_argument("--data-repo", type=Path, required=True)
    cmd.add_argument("--out", type=Path, required=True, help="the dataset folder")
    cmd.add_argument("--seasons", type=int, default=100)
    args = parser.parse_args(argv)
    if _inside_public(args.data_repo):
        print("refused: the data repository must not be inside the public repository",
              file=sys.stderr)
        return 1
    if args.command == "collect":
        return collect(args.data_repo, args.refresh, max(args.delay, DEFAULT_DELAY))
    if args.command == "build":
        out = args.out if args.out.is_absolute() else args.data_repo / args.out
        if _inside_public(out):
            print("refused: a real dataset must not be written inside the public repository",
                  file=sys.stderr)
            return 1
        result = build(args.data_repo, out, args.competition)
        players = sum(r.players for r in result.clubs)
        print(f"{len(result.clubs)} clubs, {players} players -> {out}")
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 1 if result.errors else 0
    if args.command == "correct":
        return _correct(args.data_repo, args.out if args.out.is_absolute()
                        else args.data_repo / args.out, args.record, args.field, args.value,
                        args.note)
    if args.command == "strength":
        return _strength(args.data_repo, args.out if args.out.is_absolute()
                         else args.data_repo / args.out, args.seasons)
    return 1


def _correct(data_repo: Path, out: Path, record: str, field: str, value: str, note: str) -> int:
    """Append one correction, with the current value as old_value and today's date. It is tried
    on a copy of the dataset first: a value the game would refuse is not written."""
    record_type, _, record_id = record.partition(":")
    if record_type not in corrections.KEYS or not record_id:
        print("error: --record is player:<id> or club:<id>", file=sys.stderr)
        return 1
    if not (out / "dataset.csv").exists():
        print(f"error: {out} is not a built dataset (run build)", file=sys.stderr)
        return 1
    if corrections.file_for(record_type, field, out) is None:
        print(f"error: a {record_type} has no field {field!r}", file=sys.stderr)
        return 1
    old = corrections.current_value(out, record_type, record_id, field)
    if old is None:
        print(f"error: {record} is not in {out}", file=sys.stderr)
        return 1
    correction = corrections.Correction(record_type, record_id, field, old, value,
                                        date.today().isoformat(), note)
    with tempfile.TemporaryDirectory() as tmp:
        trial = Path(tmp)
        for path in out.glob("*.csv"):
            shutil.copy(path, trial / path.name)
        corrections.apply(trial, [correction])
        problems = api.load_dataset(trial).report.errors
    if problems:
        for issue in problems:
            print(f"refused: {issue.message}", file=sys.stderr)
        return 1
    corrections.append(data_repo / "corrections.csv", correction)
    print(f"{record} {field}: {old!r} -> {value!r} (rebuild to apply)")
    return 0


def _strength(data_repo: Path, out: Path, seasons: int) -> int:
    loaded = api.load_dataset(out)
    if loaded.dataset is None:
        print(f"error: {out} is not a valid dataset (run build)", file=sys.stderr)
        return 1
    history = _inputs(data_repo).get("history", {})
    result = strength.check(loaded.dataset, seasons, history.get("champions", {}))
    names = {c.id: c.short_name for c in loaded.dataset.clubs.values()}
    print(f"{seasons} simulated Mineiros; real: {history.get('champions_years', '?')}")
    print(f"{'club':16s} {'strength':>8s} {'titles':>7s} {'real':>6s}")
    for club in sorted(result.strength, key=lambda c: -result.strength[c]):
        print(f"{names[club]:16s} {result.strength[club]:8.1f} "
              f"{result.titles.get(club, 0) / seasons:7.0%} {result.real_share((club,)):6.0%}")
    big = tuple(sorted(result.history, key=lambda c: -result.history[c]))
    for k in (2, 3):
        print(f"top {k} by real titles: simulated {result.share(big[:k]):.0%}, "
              f"real {result.real_share(big[:k]):.0%}")
    print(f"goals per first-phase match: {result.goals_per_match:.2f}")
    table = history.get("last_table", [])
    if sorted(table) == sorted(result.strength):
        ranked = sorted(table, key=lambda c: -result.strength[c])
        print(f"strength vs the last real table (reference only): Spearman "
              f"{strength.spearman(ranked, table):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
