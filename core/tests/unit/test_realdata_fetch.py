"""The polite fetcher (spec 011 R2): robots, pacing, honest user agent, cache, stop on 403/429."""

from pathlib import Path

import pytest

from manager_core.realdata.fetch import USER_AGENT, Fetcher, SourceStopped

ROBOTS = b"User-agent: *\nDisallow: /carreira\n"


class FakeWeb:
    def __init__(self, pages: dict[str, tuple[int, bytes]]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, str]] = []

    def __call__(self, url: str, user_agent: str) -> tuple[int, bytes]:
        self.calls.append((url, user_agent))
        return self.pages.get(url, (404, b""))


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _fetcher(tmp_path: Path, web: FakeWeb, t: FakeTime, refresh: bool = False) -> Fetcher:
    return Fetcher(tmp_path / "cache" / "site", delay=4.0, refresh=refresh, opener=web,
                   clock=t.clock, sleep=t.sleep, jitter=lambda: 0.0)


def test_paced_honest_and_cached(tmp_path: Path) -> None:
    web = FakeWeb({"https://x.org/robots.txt": (200, ROBOTS),
                   "https://x.org/a": (200, b"<p>a</p>"), "https://x.org/b": (200, b"<p>b</p>")})
    t = FakeTime()
    f = _fetcher(tmp_path, web, t)
    assert f.get("https://x.org/a") == "<p>a</p>"
    assert f.get("https://x.org/b") == "<p>b</p>"
    # robots, a, b: each later request waits the full delay after the previous one
    assert t.slept == [4.0, 4.0]
    assert all(agent == USER_AGENT for _, agent in web.calls)
    calls = len(web.calls)
    again = _fetcher(tmp_path, web, t)
    assert again.get("https://x.org/a") == "<p>a</p>" and len(web.calls) == calls  # from cache
    assert again.cached == 1 and again.fetched == 0
    log = (tmp_path / "cache" / "site" / "log.csv").read_text("utf-8").splitlines()
    assert log[0] == "url;fetched_at;status;bytes" and len(log) == 3


def test_refresh_fetches_again(tmp_path: Path) -> None:
    web = FakeWeb({"https://x.org/robots.txt": (200, ROBOTS), "https://x.org/a": (200, b"a")})
    t = FakeTime()
    _fetcher(tmp_path, web, t).get("https://x.org/a")
    calls = len(web.calls)
    _fetcher(tmp_path, web, t, refresh=True).get("https://x.org/a")
    assert len(web.calls) > calls


def test_robots_is_obeyed(tmp_path: Path) -> None:
    web = FakeWeb({"https://x.org/robots.txt": (200, ROBOTS)})
    with pytest.raises(SourceStopped, match="robots"):
        _fetcher(tmp_path, web, FakeTime()).get("https://x.org/carreira/1")
    assert [u for u, _ in web.calls] == ["https://x.org/robots.txt"]


@pytest.mark.parametrize("status", [403, 429])
def test_refusal_stops_the_source(tmp_path: Path, status: int) -> None:
    web = FakeWeb({"https://x.org/robots.txt": (200, ROBOTS), "https://x.org/a": (status, b""),
                   "https://x.org/b": (200, b"b")})
    f = _fetcher(tmp_path, web, FakeTime())
    with pytest.raises(SourceStopped):
        f.get("https://x.org/a")
    calls = len(web.calls)
    with pytest.raises(SourceStopped):  # stopped for the rest of the run: no more requests
        f.get("https://x.org/b")
    assert len(web.calls) == calls
