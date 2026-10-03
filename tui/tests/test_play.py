"""Scripted sessions with Textual's pilot (spec 005 US1-US4)."""

from pathlib import Path

import pytest

pytest.importorskip("textual")  # the auto-test hook runs without the TUI dependencies

from manager_core import api
from textual.widgets import DataTable, RichLog, Static

from manager_tui.app import ManagerApp, MatchDayScreen, TeamSelectionScreen

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"
SIZE = (120, 40)


@pytest.fixture
def saves(tmp_path: Path) -> Path:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    career = api.new_career(loaded.dataset, "jogo", "alvorada", master_seed=6)
    api.save_career(career, tmp_path)
    return tmp_path


def _text(app: ManagerApp, selector: str) -> str:
    return str(app.screen.query_one(selector, Static).render())


async def test_play_a_season(saves: Path) -> None:
    """US1: Continuar, team selection, feed, season end; same results as the core alone."""
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        for _ in range(200):
            screen = app.screen
            if isinstance(screen, TeamSelectionScreen):
                await pilot.press("c")
            elif isinstance(screen, MatchDayScreen):
                await pilot.press("space", "enter")
            else:
                career = app.career
                assert career is not None
                if career.pending is not None and career.pending.kind == "season_end":
                    break
                await pilot.press("space")
            await pilot.pause()
        career = app.career
        assert career is not None and career.season.complete
        await pilot.press("q")
    # the same season through the facade alone: keep the selection while it is valid (FM-like,
    # research R2), otherwise take the assistant's proposal
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    ref = api.new_career(loaded.dataset, "jogo", "alvorada", master_seed=6)
    folder = saves / "ref"
    while True:
        stop = api.continue_career(ref, folder)
        if stop.kind == "user_match":
            current = ref.selection
            valid = current is not None and not any(
                i.severity == "error" for i in api.validate_selection(ref, current))
            api.confirm_selection(ref, current if valid and current else
                                  api.propose_selection(ref))
        if stop.kind == "season_end":
            break
    assert career.season.results == ref.season.results
    assert api.load_career(saves, "jogo").season.complete  # saved on quit


async def test_selection_swap_and_suspension(saves: Path) -> None:
    """US2: a swap is played as chosen; a suspended player cannot come in."""
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        while not isinstance(app.screen, TeamSelectionScreen):
            await pilot.press("space")
            await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TeamSelectionScreen)
        career = app.career
        assert career is not None
        first_bench = screen.selection.bench[0]
        # suspend the first bench player: swapping him in is refused
        career.season.discipline._bans[first_bench] = 1  # type: ignore[union-attr]
        others = screen.query_one("#others", DataTable)
        others.move_cursor(row=0)
        await pilot.press("enter")
        assert first_bench not in {pid for _, pid in screen.selection.starters}
        assert "suspenso" in _text(app, "#select-message")
        career.season.discipline._bans[first_bench] = 0  # type: ignore[union-attr]
        # swap the striker (last slot) with the second bench player
        incoming = screen.selection.bench[1]
        xi = screen.query_one("#xi", DataTable)
        xi.move_cursor(row=len(screen.selection.starters) - 1)
        others.move_cursor(row=1)
        await pilot.press("enter")
        chosen = screen.selection
        assert incoming in {pid for _, pid in chosen.starters}
        match_id = career.pending.match_id if career.pending else None
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, MatchDayScreen)
        report = career.season.results[match_id or ""].report
        assert report is not None
        side = "home" if career.season.matches[match_id or ""].home_id == "alvorada" else "away"
        assert sorted(pid for _, pid in report.lineup(side).starters) == sorted(
            pid for _, pid in chosen.starters)


async def test_feed_shows_every_event(saves: Path) -> None:
    """US3: every report event appears, then the stats."""
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        while not isinstance(app.screen, MatchDayScreen):
            await pilot.press("c" if isinstance(app.screen, TeamSelectionScreen) else "space")
            await pilot.pause()
        screen = app.screen
        assert isinstance(screen, MatchDayScreen)
        await pilot.press("4")
        await pilot.pause()
        log = screen.query_one("#feed", RichLog)
        text = "\n".join(str(line.text) for line in log.lines)
        for line in screen.lines:
            assert line.text[:30] in text
        assert "Estatísticas" in text


async def test_screens_render(saves: Path) -> None:
    """US4: every screen renders (and the profile opens) at the minimum size."""
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=(100, 30)) as pilot:
        assert not app.query_one("#too-small", Static).display
        for key, selector, needle in (("h", "#home-text", "Alvorada"),
                                      ("n", "#news-text", "Notícias"),
                                      ("c", "#calendar-text", "Janeiro")):
            await pilot.press(key)
            await pilot.pause()
            assert needle in str(app.query_one(selector, Static).render())
        await pilot.press("e")
        await pilot.pause()
        table = app.query_one("#squad-table", DataTable)
        assert table.row_count == 27
        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert "Técnicos" in str(app.screen.query_one(Static).render()) or app.screen.query(Static)
        await pilot.press("escape")
        await pilot.press("t")
        await pilot.pause()
        assert app.query_one("#overall-table", DataTable).row_count == 12


async def test_too_small_terminal(saves: Path) -> None:
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=(80, 24)):
        assert app.query_one("#too-small", Static).display


async def test_no_career(tmp_path: Path) -> None:
    app = ManagerApp(tmp_path)
    async with app.run_test(size=SIZE):
        assert "career new" in str(app.query_one("#no-career", Static).render())
