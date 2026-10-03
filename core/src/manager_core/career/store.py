"""Career saves: one SQLite file per save (spec 004, contracts/save-format.md).

A save holds the world at the start of the season (001's canonical CSV texts), the season
definition (ruleset TOML, year, seed, participants), the played results with their reports,
the career fields and the history. Loading rebuilds the season and replays it with the stored
results. Writes are atomic: a temporary file replaces the old one only once it is complete.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from manager_core import __version__
from manager_core.career.career import (
    Career,
    build_season,
    record_from_json,
    record_to_json,
    stop_from_json,
    stop_to_json,
)
from manager_core.career.codec import decode_result, encode_result
from manager_core.career.recorded import RecordedProvider
from manager_core.career.selection import Selection
from manager_core.domain.dataset import Dataset
from manager_core.i18n import t
from manager_core.io import reader, writer

FORMAT_VERSION = 2  # 2: the user's team selection (spec 005)
AUTOSAVE = "autosave"
SUFFIX = ".sqlite"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
# Migrations: MIGRATIONS[n] upgrades a file from format n to n + 1.
def _v1_to_v2(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS selection (selection_json TEXT NOT NULL)")


MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {1: _v1_to_v2}

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE career (name TEXT NOT NULL, master_seed INTEGER NOT NULL,
    user_club_id TEXT NOT NULL, game_date TEXT NOT NULL, last_autosave TEXT NOT NULL,
    pending_json TEXT);
CREATE TABLE world_files (name TEXT PRIMARY KEY, text TEXT NOT NULL);
CREATE TABLE season (ruleset_toml TEXT NOT NULL, year INTEGER NOT NULL,
    master_seed INTEGER NOT NULL, participants_json TEXT NOT NULL);
CREATE TABLE results (match_id TEXT PRIMARY KEY, result_json TEXT NOT NULL);
CREATE TABLE history (year INTEGER PRIMARY KEY, record_json TEXT NOT NULL);
CREATE TABLE selection (selection_json TEXT NOT NULL);
"""


class SaveError(Exception):
    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.message = t(f"save.{code}", **params)
        super().__init__(f"{code}: {self.message}")


class SaveNotFoundError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


@dataclass(frozen=True, slots=True)
class SaveSummary:
    name: str
    user_club_id: str
    current_date: date
    year: int
    saved_at: str


def check_name(name: str, allow_autosave: bool = False) -> str:
    if not NAME.match(name) or (name == AUTOSAVE and not allow_autosave):
        raise SaveError("V005", name=name)
    return name


def path_for(saves: Path, name: str) -> Path:
    return saves / f"{name}{SUFFIX}"


def _world_texts(world: Dataset) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        writer.write(world, Path(tmp))
        return {p.name: p.read_text("utf-8") for p in sorted(Path(tmp).iterdir())}


def _world_from(texts: dict[str, str]) -> Dataset:
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in texts.items():
            Path(tmp, name).write_text(text, "utf-8", newline="")
        loaded = reader.load(Path(tmp))
    if loaded.dataset is None:
        raise SaveError("V004")
    return loaded.dataset


def save(career: Career, saves: Path, name: str | None = None,
         allow_autosave: bool = False) -> Path:
    name = check_name(career.name if name is None else name, allow_autosave)
    saves.mkdir(parents=True, exist_ok=True)
    target = path_for(saves, name)
    tmp = target.with_suffix(SUFFIX + ".tmp")
    tmp.unlink(missing_ok=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")  # display only, never a sim input
    created = now
    if target.is_file():
        try:
            with sqlite3.connect(target) as old:
                row = old.execute("SELECT value FROM meta WHERE key = 'created_at'").fetchone()
                created = row[0] if row else now
            old.close()
        except sqlite3.Error:
            pass
    conn = sqlite3.connect(tmp)
    try:
        conn.executescript(SCHEMA)
        conn.execute(f"PRAGMA user_version = {FORMAT_VERSION}")
        conn.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("core_version", __version__), ("python_version", platform.python_version()),
            ("created_at", created), ("saved_at", now)])
        conn.execute("INSERT INTO career VALUES (?, ?, ?, ?, ?, ?)", (
            career.name, career.master_seed, career.user_club_id,
            career.current_date.isoformat(), career.last_autosave.isoformat(),
            json.dumps(stop_to_json(career.pending))))
        conn.executemany("INSERT INTO world_files VALUES (?, ?)",
                         sorted(_world_texts(career.world).items()))
        season = career.season
        conn.execute("INSERT INTO season VALUES (?, ?, ?, ?)", (
            career.ruleset_toml, season.year, season.master_seed,
            json.dumps(list(season.participants))))
        conn.executemany("INSERT INTO results VALUES (?, ?)", [
            (mid, json.dumps(encode_result(r), sort_keys=True))
            for mid, r in sorted(season.results.items())])
        if career.selection is not None:
            sel = career.selection
            conn.execute("INSERT INTO selection VALUES (?)", (json.dumps({
                "formation": sel.formation, "starters": [list(s) for s in sel.starters],
                "bench": list(sel.bench)}),))
        conn.executemany("INSERT INTO history VALUES (?, ?)", [
            (r.year, json.dumps(record_to_json(r), sort_keys=True)) for r in career.history])
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, target)
    return target


def _migrate(conn: sqlite3.Connection, version: int) -> None:
    if version > FORMAT_VERSION:
        raise SaveError("V001", version=version, supported=FORMAT_VERSION)
    while version < FORMAT_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise SaveError("V002", version=version)
        step(conn)
        version += 1


def load(saves: Path, name: str) -> Career:
    path = path_for(saves, name)
    if not path.is_file():
        raise SaveNotFoundError(name)
    conn = sqlite3.connect(path)
    try:
        _migrate(conn, conn.execute("PRAGMA user_version").fetchone()[0])
        c = conn.execute("SELECT * FROM career").fetchone()
        texts = dict(conn.execute("SELECT name, text FROM world_files").fetchall())
        ruleset_toml, year, master_seed, participants = conn.execute(
            "SELECT * FROM season").fetchone()
        stored = dict(conn.execute("SELECT match_id, result_json FROM results").fetchall())
        history = [record_from_json(json.loads(r)) for (r,) in conn.execute(
            "SELECT record_json FROM history ORDER BY year").fetchall()]
        sel_row = conn.execute("SELECT selection_json FROM selection").fetchone()
    except sqlite3.Error as exc:
        raise SaveError("V003", detail=str(exc)) from exc
    finally:
        conn.close()
    world = _world_from(texts)
    try:
        recorded = {mid: decode_result(json.loads(js)) for mid, js in stored.items()}
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveError("V003", detail=str(exc)) from exc
    season = build_season(world, ruleset_toml, year, master_seed, json.loads(participants),
                          recorded)
    current = date.fromisoformat(c[3])
    if current > season.current_date:
        season.advance_to(current)
    provider = season.provider
    assert isinstance(provider, RecordedProvider)
    unknown = set(recorded) - provider.used
    if unknown:
        raise SaveError("V003", detail=", ".join(sorted(unknown)[:3]))
    selection = None
    if sel_row is not None:
        d = json.loads(sel_row[0])
        selection = Selection(d["formation"], tuple((i, pid) for i, pid in d["starters"]),
                              tuple(d["bench"]))
    return Career(c[0], c[1], c[2], current, date.fromisoformat(c[4]), world, ruleset_toml,
                  season, history, stop_from_json(json.loads(c[5]) if c[5] else None),
                  selection)


def list_saves(saves: Path) -> list[SaveSummary]:
    summaries = []
    for path in sorted(saves.glob(f"*{SUFFIX}")) if saves.is_dir() else []:
        try:
            with sqlite3.connect(path) as conn:
                c = conn.execute("SELECT user_club_id, game_date FROM career").fetchone()
                year = conn.execute("SELECT year FROM season").fetchone()[0]
                saved = conn.execute(
                    "SELECT value FROM meta WHERE key = 'saved_at'").fetchone()[0]
            conn.close()
        except (sqlite3.Error, TypeError):
            continue
        summaries.append(SaveSummary(path.stem, c[0], date.fromisoformat(c[1]), year, saved))
    return sorted(summaries, key=lambda s: (s.saved_at, s.name), reverse=True)


def delete(saves: Path, name: str) -> None:
    check_name(name)
    path = path_for(saves, name)
    if not path.is_file():
        raise SaveNotFoundError(name)
    path.unlink()
