"""The terminal game (spec 005). Every rule comes from `manager_core.api`; this module only shows
views and sends the owner's choices back (Constitution III)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manager_core import api
from manager_core.i18n import t
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import ContentSwitcher, DataTable, Footer, RichLog, Static

MIN_SIZE = (100, 30)
VIEWS = ("home", "squad", "tables", "calendar", "news")
SPEEDS = {"1": 0.8, "2": 0.3, "3": 0.05}  # seconds per feed line; 4 = instant
FORMATIONS = ("4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2")
MONTHS = 12


def default_saves() -> Path:
    return Path(__file__).resolve().parents[3] / "saves"


def _stars(value: float) -> str:
    return "★" * int(value) + ("½" if value % 1 else "")


def _date(day: Any) -> str:
    return f"{t(f'weekday.{day.weekday()}')} {day:%d/%m/%Y}"


def _match_text(m: api.MatchView) -> str:
    score = "x" if m.result is None else f"{m.result.home_goals} x {m.result.away_goals}"
    return f"{_date(m.kickoff)} {m.kickoff:%H:%M}  {m.home_name} {score} {m.away_name}"


# ---- views ------------------------------------------------------------------------------------


class HomeView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static(id="home-text")

    def refresh_view(self, career: api.Career) -> None:
        status = api.career_status(career)
        lines = [f"[b]{status.club_name}[/b]",
                 t("ui.home.date", date=_date(status.current_date), year=status.year), ""]
        if status.position is not None:
            lines.append(t("ui.home.position", place=status.position))
        lines.append(f"[b]{t('ui.home.next_match')}[/b]")
        lines.append(_match_text(status.next_match) if status.next_match
                     else t("ui.home.no_match"))
        lines += ["", f"[b]{t('ui.home.latest_news')}[/b]"]
        lines += [f"{n.day:%d/%m} {n.text}" for n in api.career_news(career)[:8]]
        self.query_one("#home-text", Static).update("\n".join(lines))


class SquadView(Vertical):
    def compose(self) -> ComposeResult:
        yield Static(id="squad-title")
        yield DataTable(id="squad-table", cursor_type="row")

    def refresh_view(self, career: api.Career) -> None:
        status = api.career_status(career)
        self.query_one("#squad-title", Static).update(
            f"[b]{t('ui.squad.title', club=status.club_name)}[/b]")
        table = self.query_one("#squad-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("ui.select.player"), t("ui.select.pos"), t("ui.squad.age"),
                          t("ui.select.stars"), t("ui.select.status"), t("ui.squad.apps"),
                          t("ui.squad.goals"), t("ui.squad.assists"), t("ui.squad.cards"))
        for row in api.squad_view(career):
            status_text = (t("ui.select.suspended") if row.suspended else
                           t("ui.squad.yellows_count", n=row.yellows) if row.yellows else "")
            table.add_row(row.name, row.position.value, row.age, _stars(row.stars), status_text,
                          row.appearances, row.goals, row.assists,
                          f"{row.yellow_cards}/{row.red_cards}", key=row.player_id)


class TablesView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static(id="tables-title")
        yield DataTable(id="overall-table", cursor_type="row")
        yield Static(id="fixtures-title")
        yield Static(id="fixtures-text")

    def refresh_view(self, career: api.Career) -> None:
        season = career.season
        self.query_one("#tables-title", Static).update(f"[b]{t('ui.tables.overall')}[/b]")
        table = self.query_one("#overall-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*[t(f"table.{k}") for k in ("pos", "club", "p", "w", "d", "l", "gf",
                                                       "ga", "gd", "pts")])
        for r in api.season_table(season):
            table.add_row(r.place, season.club_name(r.club_id), r.played, r.won, r.drawn,
                          r.lost, r.goals_for, r.goals_against, r.goal_difference, r.points)
        club = career.user_club_id
        self.query_one("#fixtures-title", Static).update(
            f"\n[b]{t('ui.tables.fixtures', club=season.club_name(club))}[/b]")
        self.query_one("#fixtures-text", Static).update(
            "\n".join(_match_text(m) for m in api.season_fixtures(season, club_id=club)))


class CalendarView(VerticalScroll):
    month = 1

    def compose(self) -> ComposeResult:
        yield Static(id="calendar-text")

    def refresh_view(self, career: api.Career) -> None:
        season = career.season
        club = career.user_club_id
        lines = [f"[b]{t('ui.calendar.title', month=t(f'month.{self.month}').capitalize(),
                                                year=season.year)}[/b]",
                 t("ui.calendar.help"), ""]
        for day in api.season_calendar(season, self.month):
            windows = ", ".join(dict.fromkeys(w.name for w in day.windows))
            mine = [api.match_view(season, mid) for mid in day.match_ids
                    if club in (season.matches[mid].home_id, season.matches[mid].away_id)]
            marker = "●" if mine else (f"{len(day.match_ids)} jogos" if day.match_ids else "")
            line = f"{_date(day.day)}  {marker}"
            if mine:
                line += f"  [b]{mine[0].home_name} x {mine[0].away_name}[/b]"
            if windows:
                line += f"  [{windows}]"
            lines.append(line)
        self.query_one("#calendar-text", Static).update("\n".join(lines))


class NewsView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static(id="news-text")

    def refresh_view(self, career: api.Career) -> None:
        lines = [f"[b]{t('ui.news.title')}[/b]", ""]
        lines += [f"{_date(n.day)}  {n.text}" for n in api.career_news(career)]
        self.query_one("#news-text", Static).update("\n".join(lines))


# ---- modal screens ----------------------------------------------------------------------------


class PlayerProfileScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "app.pop_screen", t("ui.profile.close"))]

    def __init__(self, career: api.Career, player_id: str) -> None:
        super().__init__()
        self.career = career
        self.player_id = player_id

    def compose(self) -> ComposeResult:
        p = api.player_profile(self.career.world, self.player_id)
        lines = [f"[b]{p.full_name}[/b] ({p.display_name})", f"{p.age} · {p.best_position.value}"]
        for group in p.attributes:
            values = "  ".join(f"{t(f'attr.{name}')}: {v}" for name, v in group.values)
            lines += ["", f"[b]{t(f'group.{group.group.value}')}[/b]", values]
        lines += ["", t("ui.profile.close")]
        yield VerticalScroll(Static("\n".join(lines)), id="dialog")


class TeamSelectionScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("enter", "swap", "Trocar"),
        Binding("tab", "focus_next", "Lista", show=False),
        Binding("f", "formation", "Formação"),
        Binding("a", "assistant", "Assistente"),
        Binding("c", "confirm", "Confirmar"),
        Binding("escape", "cancel", "Voltar"),
    ]

    def __init__(self, career: api.Career) -> None:
        super().__init__()
        self.career = career
        current = career.selection
        valid = current is not None and not any(
            i.severity == "error" for i in api.validate_selection(career, current))
        self.selection = current if valid and current else api.propose_selection(career)
        self.warned = False

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(id="select-title")
            with Horizontal():
                yield DataTable(id="xi", cursor_type="row")
                yield DataTable(id="others", cursor_type="row")
            yield Static(id="select-message")
            yield Static(t("ui.select.help"))

    def on_mount(self) -> None:
        self._redraw()
        self.query_one("#xi", DataTable).focus()

    def _rows(self) -> dict[str, api.SquadRow]:
        return {r.player_id: r for r in api.squad_view(self.career)}

    def _redraw(self) -> None:
        rows = self._rows()
        sel = self.selection
        club = api.career_status(self.career).club_name
        self.query_one("#select-title", Static).update(
            f"[b]{t('ui.select.title', club=club, formation=sel.formation)}[/b]")
        positions = api.formation_positions(sel.formation)
        xi = self.query_one("#xi", DataTable)
        others = self.query_one("#others", DataTable)
        for table in (xi, others):
            table.clear(columns=True)
            table.add_columns(t("ui.select.slot"), t("ui.select.player"), t("ui.select.pos"),
                              t("ui.select.stars"), t("ui.select.status"))
        for slot, pid in sel.starters:
            r = rows[pid]
            xi.add_row(positions[slot], r.name, r.position.value, _stars(r.stars),
                       self._status(r), key=str(slot))
        rest = [*sel.bench, *[pid for pid in rows if pid not in sel.players]]
        for pid in rest:
            r = rows[pid]
            others.add_row(t("ui.select.bench") if pid in sel.bench else "", r.name,
                           r.position.value, _stars(r.stars), self._status(r), key=pid)

    @staticmethod
    def _status(row: api.SquadRow) -> str:
        return t("ui.select.suspended") if row.suspended else ""

    def _message(self, text: str) -> None:
        self.query_one("#select-message", Static).update(text)

    def action_swap(self) -> None:
        xi = self.query_one("#xi", DataTable)
        others = self.query_one("#others", DataTable)
        if xi.row_count == 0 or others.row_count == 0:
            return
        slot = int(xi.coordinate_to_cell_key(xi.cursor_coordinate).row_key.value or 0)
        incoming = str(others.coordinate_to_cell_key(others.cursor_coordinate).row_key.value)
        swapped = api.swap_in_selection(self.career, self.selection, slot, incoming)
        problems = [i for i in api.validate_selection(self.career, swapped)
                    if i.code == "suspended" and i.player_id == incoming]
        if problems:
            name = self._rows()[incoming].name
            self._message(t("ui.select.refused_suspended", player=name))
            return
        self.selection = swapped
        self.warned = False
        self._message("")
        self._redraw()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()  # Enter on either list swaps the highlighted players
        self.action_swap()

    def action_formation(self) -> None:
        index = (FORMATIONS.index(self.selection.formation) + 1) % len(FORMATIONS)
        self.selection = api.propose_selection(self.career, FORMATIONS[index])
        self._redraw()

    def action_assistant(self) -> None:
        self.selection = api.propose_selection(self.career, self.selection.formation)
        self._redraw()

    def action_confirm(self) -> None:
        issues = api.validate_selection(self.career, self.selection)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            self._message(t("ui.select.errors", problems=", ".join(i.code for i in errors)))
            return
        if issues and not self.warned:
            self.warned = True
            self._message(t("ui.select.no_goalkeeper"))
            return
        api.confirm_selection(self.career, self.selection)
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class MatchDayScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("1", "speed('1')", "Lento"),
        Binding("2", "speed('2')", "Normal"),
        Binding("3", "speed('3')", "Rápido"),
        Binding("4", "instant", "Instantâneo"),
        Binding("space", "instant", "Pular", show=False),
        Binding("enter", "close", "Continuar"),
        Binding("escape", "close", "Continuar", show=False),
    ]

    def __init__(self, career: api.Career, match_id: str, speed: str = "2") -> None:
        super().__init__()
        self.career = career
        self.match_id = match_id
        self.lines = api.match_feed(career.season, match_id)
        self.shown = 0
        self.speed = speed
        self.timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[b]{t('ui.match.title')}[/b]", id="match-title")
            yield RichLog(id="feed", wrap=True, markup=True)
            yield Static(t("ui.match.help"))

    def on_mount(self) -> None:
        self._start()

    def _start(self) -> None:
        if self.timer is not None:
            self.timer.stop()
        self.timer = self.set_interval(SPEEDS[self.speed], self._next_line)

    def _next_line(self) -> None:
        if self.shown >= len(self.lines):
            self._finish()
            return
        line = self.lines[self.shown]
        self.shown += 1
        minute = "" if line.kind == "kickoff" else f"{line.minute}'"
        self.query_one("#feed", RichLog).write(f"{minute:>6}  {line.text}")

    def _finish(self) -> None:
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
        if self.shown > len(self.lines):
            return
        self.shown = len(self.lines) + 1
        log = self.query_one("#feed", RichLog)
        log.write("")
        log.write(f"[b]{t('ui.match.final')}[/b]")
        for line in api.match_stat_lines(self.career.season, self.match_id):
            log.write(line)

    def action_speed(self, speed: str) -> None:
        self.speed = speed
        if self.shown <= len(self.lines):
            self._start()

    def action_instant(self) -> None:
        while self.shown < len(self.lines):
            self._next_line()
        self._finish()

    def action_close(self) -> None:
        self.action_instant()
        self.dismiss(None)


# ---- the app ----------------------------------------------------------------------------------


class ManagerApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = t("ui.title")
    BINDINGS = [
        Binding("h", "show('home')", t("ui.menu.home")),
        Binding("e", "show('squad')", t("ui.menu.squad")),
        Binding("t", "show('tables')", t("ui.menu.tables")),
        Binding("c", "show('calendar')", t("ui.menu.calendar")),
        Binding("n", "show('news')", t("ui.menu.news")),
        Binding("space", "continue_game", t("ui.continue")),
        Binding("[", "month(-1)", "", show=False),
        Binding("]", "month(1)", "", show=False),
        Binding("q", "quit_game", t("ui.quit")),
    ]

    def __init__(self, saves: Path, career_name: str | None = None) -> None:
        super().__init__()
        self.saves = saves
        self.career: api.Career | None = None
        names = [s.name for s in api.list_saves(saves)]
        name = career_name or next((n for n in names if n != "autosave"), None)
        if name is not None:
            self.career = api.load_career(saves, name)

    def compose(self) -> ComposeResult:
        yield Static(t("ui.too_small"), id="too-small")
        if self.career is None:
            yield Static(t("ui.no_career"), id="no-career")
            yield Footer()
            return
        with Horizontal(id="main"):
            yield Static("\n".join(f"[b]{key.upper()}[/b] {t(f'ui.menu.{view}')}"
                                   for key, view in zip("hetcn", VIEWS, strict=True))
                         + f"\n\n[b]␣[/b] {t('ui.continue')}\n[b]Q[/b] {t('ui.quit')}",
                         id="sidebar")
            with ContentSwitcher(initial="home", id="views"):
                yield HomeView(id="home")
                yield SquadView(id="squad")
                yield TablesView(id="tables")
                yield CalendarView(id="calendar")
                yield NewsView(id="news")
        yield Footer()

    def on_mount(self) -> None:
        self._check_size()
        if self.career is not None:
            today = self.career.current_date
            in_season = today.year == self.career.season.year
            self.query_one(CalendarView).month = today.month if in_season else 1
            self.refresh_views()

    def on_resize(self) -> None:
        self._check_size()

    def _check_size(self) -> None:
        small = self.size.width < MIN_SIZE[0] or self.size.height < MIN_SIZE[1]
        self.query_one("#too-small", Static).display = small

    def refresh_views(self) -> None:
        if self.career is None:
            return
        self.query_one(HomeView).refresh_view(self.career)
        self.query_one(SquadView).refresh_view(self.career)
        self.query_one(TablesView).refresh_view(self.career)
        self.query_one(CalendarView).refresh_view(self.career)
        self.query_one(NewsView).refresh_view(self.career)

    def action_show(self, view: str) -> None:
        if self.career is not None:
            self.query_one(ContentSwitcher).current = view

    def action_month(self, step: int) -> None:
        if self.career is None:
            return
        calendar = self.query_one(CalendarView)
        calendar.month = (calendar.month - 1 + step) % MONTHS + 1
        calendar.refresh_view(self.career)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self.career is not None and event.data_table.id == "squad-table":
            self.push_screen(PlayerProfileScreen(self.career, str(event.row_key.value)))

    # -- the loop ------------------------------------------------------------------------------

    def action_continue_game(self) -> None:
        career = self.career
        if career is None:
            return
        if career.pending is not None and career.pending.kind == "user_match":
            self.push_screen(TeamSelectionScreen(career), self._after_selection)
            return
        self._handle_stop(api.continue_career(career, self.saves))

    def _handle_stop(self, stop: api.Stop) -> None:
        assert self.career is not None
        self.refresh_views()
        if stop.kind == "user_match":
            self.push_screen(TeamSelectionScreen(self.career), self._after_selection)
        elif stop.kind == "event":
            self.notify(t("ui.stop.event", date=_date(stop.day)))
        else:
            self.notify(t("ui.stop.season_end", year=self.career.season.year))

    def _after_selection(self, confirmed: bool | None) -> None:
        career = self.career
        if not confirmed or career is None or career.pending is None:
            return
        match_id = career.pending.match_id
        stop = api.continue_career(career, self.saves)  # plays the match day, on to the next stop
        self.refresh_views()
        if match_id is not None:
            self.push_screen(MatchDayScreen(career, match_id),
                             lambda _: self._handle_stop(stop))

    def action_quit_game(self) -> None:
        if self.career is not None:
            api.save_career(self.career, self.saves)
        self.exit()
