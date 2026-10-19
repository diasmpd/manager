"""A polite fetcher for the real-data import (spec 011 R2).

Every page is fetched at most once and cached gzipped in the private data repository; a host is
asked at most once every `delay` seconds; robots.txt is obeyed; the user agent says who we are.
A source that answers 403 or 429 is stopped for the rest of the run (no retry loops).
"""

from __future__ import annotations

import gzip
import hashlib
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

USER_AGENT = ("manager-private-import/0.1 (personal, non-public football game; "
              "github.com/diasmpd/manager)")
DEFAULT_DELAY = 4.0
STOP_STATUSES = frozenset({403, 429})

# (url, user agent) -> (status, body); replaced in tests
Opener = Callable[[str, str], tuple[int, bytes]]


class SourceStopped(RuntimeError):
    """The source refused us (403/429) or robots.txt forbids the page: stop, do not retry."""


def _urllib_open(url: str, user_agent: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status), bytes(response.read())
    except urllib.error.HTTPError as error:
        return int(error.code), b""


def decode(body: bytes) -> str:
    """Page bytes as text, in the charset the page declares (ogol is not UTF-8); UTF-8 when it
    declares none, Windows-1252 when that fails."""
    head = body[:16384].decode("ascii", errors="ignore").lower()
    match = re.search(r"""charset=["']?([a-z0-9_-]+)""", head)
    if match:
        try:
            return body.decode(match.group(1), errors="replace")
        except LookupError:
            pass
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", errors="replace")


@dataclass
class Fetcher:
    cache_dir: Path  # <data repo>/cache/<source>
    delay: float = DEFAULT_DELAY
    refresh: bool = False
    opener: Opener = _urllib_open
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    jitter: Callable[[], float] = field(default=lambda: random.uniform(0.0, 1.5))
    _last: dict[str, float] = field(default_factory=dict)
    _robots: dict[str, urllib.robotparser.RobotFileParser] = field(default_factory=dict)
    stopped: str | None = None
    fetched: int = 0
    cached: int = 0

    def get(self, url: str) -> str:
        """The page's text: from the cache, or fetched (politely) and cached."""
        if self.stopped is not None:
            raise SourceStopped(self.stopped)
        path = self.cache_path(url)
        if path.exists() and not self.refresh:
            self.cached += 1
            return decode(gzip.decompress(path.read_bytes()))
        if not self._allowed(url):
            raise SourceStopped(f"robots.txt disallows {url}")
        status, body = self._polite_open(url)
        self._log(url, status, len(body))
        if status in STOP_STATUSES:
            self.stopped = f"HTTP {status} from {urllib.parse.urlsplit(url).netloc}: stopped"
            raise SourceStopped(self.stopped)
        if status != 200:
            raise SourceStopped(f"HTTP {status} for {url}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(body, mtime=0))
        self.fetched += 1
        return decode(body)

    def cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".html.gz")

    def _allowed(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        robots = self._robots.get(host)
        if robots is None:
            robots = urllib.robotparser.RobotFileParser()
            status, body = self._polite_open(host + "/robots.txt")
            robots.parse(body.decode("utf-8", errors="replace").splitlines() if status == 200
                         else [])
            self._robots[host] = robots
        return robots.can_fetch(USER_AGENT, url)

    def _polite_open(self, url: str) -> tuple[int, bytes]:
        host = urllib.parse.urlsplit(url).netloc
        last = self._last.get(host)
        if last is not None:
            wait = self.delay + self.jitter() - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        result = self.opener(url, USER_AGENT)
        self._last[host] = self.clock()
        return result

    def _log(self, url: str, status: int, size: int) -> None:
        log = self.cache_dir / "log.csv"
        log.parent.mkdir(parents=True, exist_ok=True)
        new = not log.exists()
        with log.open("a", encoding="utf-8", newline="\n") as handle:
            if new:
                handle.write("url;fetched_at;status;bytes\n")
            stamp = datetime.now(UTC).isoformat(timespec="seconds")
            handle.write(f"{url};{stamp};{status};{size}\n")
