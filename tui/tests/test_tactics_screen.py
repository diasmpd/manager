"""The Tactics screen with Textual's pilot (spec 006 T014)."""

from pathlib import Path

import pytest

pytest.importorskip("textual")  # the auto-test hook runs without the TUI dependencies

from manager_core import api
from textual.widgets import DataTable, Static

from manager_tui.app import ManagerApp, TacticsScreen, TeamSelectionScreen

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"
SIZE = (140, 50)


@pytest.fixture
def saves(tmp_path: Path) -> Path:
    loaded = api.load_dataset(SAMPLE)
    assert loaded.dataset is not None
    career = api.new_career(loaded.dataset, "jogo", "alvorada", master_seed=6)
    api.save_career(career, tmp_path)
    return tmp_path


def _cells(screen: TacticsScreen, table_id: str) -> list[list[str]]:
    table = screen.query_one(f"#{table_id}", DataTable)
    return [[str(c) for c in table.get_row_at(i)] for i in range(table.row_count)]


async def test_change_mentality_and_an_instruction_then_confirm(saves: Path) -> None:
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("x")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TacticsScreen)
        rows = _cells(screen, "instructions")
        assert rows[2][1] == "Equilibrada" or rows[2][0] == "Mentalidade"
        await pilot.press("down", "down", "enter")  # mentality: balanced -> positive
        await pilot.press("down", "down", "enter")  # first team instruction, one step
        await pilot.pause()
        assert screen.tactic.mentality == "positive"
        first = api.tactic_options().team[0]
        assert screen.tactic.setting(first.id) != first.default
        await pilot.press("c")
        await pilot.pause()
        assert not isinstance(app.screen, TacticsScreen)
        career = app.career
        assert career is not None and career.tactic is not None
        assert career.tactic.mentality == "positive"
        await pilot.press("q")
    # the tactic was saved with the career
    assert api.load_career(saves, "jogo").tactic == career.tactic


async def test_roles_show_suitability_and_locks(saves: Path) -> None:
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("x")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TacticsScreen)
        slots = _cells(screen, "slots")
        assert len(slots) == 11
        assert all("(" in row[2] and "(" in row[3] for row in slots)  # suitability shown
        # cycle a slot's IP role until one locks an instruction, and see it marked
        await pilot.press("tab")
        await pilot.pause()
        assert screen.focused is screen.query_one("#slots", DataTable)
        await pilot.press("down")  # a defender: roles there lock instructions in the data
        locked_seen = False
        for _ in range(8):
            await pilot.press("enter")
            await pilot.pause()
            if any("🔒" in row[1] for row in _cells(screen, "player-instructions")):
                locked_seen = True
                break
        assert locked_seen
        assert api.validate_tactic(screen.career, screen.tactic) == []
        await pilot.press("escape")
        await pilot.pause()
        assert app.career is not None and app.career.tactic is None  # cancelled


async def test_reachable_from_team_selection(saves: Path) -> None:
    app = ManagerApp(saves, "jogo")
    async with app.run_test(size=SIZE) as pilot:
        for _ in range(60):
            if isinstance(app.screen, TeamSelectionScreen):
                break
            await pilot.press("space")
            await pilot.pause()
        assert isinstance(app.screen, TeamSelectionScreen)
        await pilot.press("tab")  # Tab moves between the two lists (regression: it did not)
        await pilot.pause()
        assert app.screen.focused is app.screen.query_one("#others", DataTable)
        await pilot.press("x")
        await pilot.pause()
        assert isinstance(app.screen, TacticsScreen)
        title = str(app.screen.query_one("#tactics-title", Static).render())
        assert "Tática" in title
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, TeamSelectionScreen)
