"""`python -m manager_core.server --saves DIR`: the core behind the local API (spec 007).

The Godot client starts this as a child process and talks to it over stdin/stdout, one JSON
message per line (contracts/local-api.md)."""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from manager_core.server.methods import METHODS, Config, map_errors
from manager_core.server.protocol import Session, serve

REPO = Path(__file__).resolve().parents[4]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="manager_core.server")
    parser.add_argument("--saves", type=Path, default=REPO / "saves")
    parser.add_argument("--data", type=Path, default=REPO / "data" / "sample")
    args = parser.parse_args(argv)
    args.saves.mkdir(parents=True, exist_ok=True)
    # UTF-8 both ways, whatever the console code page (pythonw has no console at all)
    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", newline="\n")
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n",
                              line_buffering=True)
    session = Session(stdout)
    session.state["config"] = Config(args.saves, args.data)
    serve(session, METHODS, stdin, map_errors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
