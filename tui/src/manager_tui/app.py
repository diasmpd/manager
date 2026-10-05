"""The terminal game (spec 005). Every rule comes from `manager_core.api`; this module only shows
views and sends the owner's choices back (Constitution III)."""

from __future__ import annotations

import dataclasses
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
        Binding("tab", "app.focus_next", "Lista", show=False),
        Binding("f", "formation", "Formação"),
        Binding("a", "assistant", "Assistente"),
        Binding("x", "tactics", "Tática"),
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
        changes = api.tactic_changes(self.career, self.selection.formation)
        api.confirm_selection(self.career, self.selection)
        if changes:
            self.app.notify(t("ui.tactics.refitted", positions=", ".join(changes)))
        self.dismiss(True)

    def action_tactics(self) -> None:
        # the tactic follows the formation on screen; confirm the XI first to change it
        self.app.push_screen(TacticsScreen(self.career))

    def action_cancel(self) -> None:
        self.dismiss(False)


class TacticsScreen(ModalScreen[bool]):
    """The user's tactic (spec 006 T014): formations, mentality, team instructions by phase,
    IP and OOP roles per slot with suitability, player instructions (locked ones marked) and
    set-piece takers. Every rule is the core's; this screen only cycles the options it lists."""

    BINDINGS = [
        Binding("enter", "cycle", "Mudar", show=False),
        Binding("o", "cycle_oop", "Função sem a bola"),
        Binding("tab", "app.focus_next", "Próxima lista", show=False),
        Binding("r", "reset", "Padrão"),
        Binding("c", "confirm", "Confirmar"),
        Binding("escape", "cancel", "Voltar"),
    ]

    def __init__(self, career: api.Career, live: api.LiveSession | None = None) -> None:
        super().__init__()
        self.career = career
        self.live = live  # spec 008: a change during a live match acts from this minute
        self.options = api.tactic_options()
        self.tactic = (api.live_state(career, live).tactic if live is not None
                       else api.current_tactic(career))
        selection = career.selection or api.propose_selection(career, self.tactic.ip_formation)
        self.players = dict(selection.starters)
        self.slot = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(id="tactics-title")
            with Horizontal():
                yield DataTable(id="instructions", cursor_type="row")
                with Vertical():
                    yield DataTable(id="slots", cursor_type="row")
                    yield DataTable(id="player-instructions", cursor_type="row")
                    yield DataTable(id="takers", cursor_type="row")
            yield Static(id="tactics-message")
            yield Static(t("ui.tactics.help"))

    def on_mount(self) -> None:
        self._redraw()
        self.query_one("#instructions", DataTable).focus()

    # -- drawing -------------------------------------------------------------------------------

    def _names(self) -> dict[str, str]:
        return {r.player_id: r.name for r in api.squad_view(self.career)}

    @staticmethod
    def _label(option: Any, setting: str) -> str:
        return str(option.labels[option.settings.index(setting)])

    def _redraw(self) -> None:
        tactic = self.tactic
        mentality = self._label(self.options.mentality, tactic.mentality)
        club = api.career_status(self.career).club_name
        self.query_one("#tactics-title", Static).update(f"[b]{t(
            'ui.tactics.title', club=club, ip=tactic.ip_formation, oop=tactic.oop_formation,
            mentality=mentality)}[/b]")
        self._draw_instructions()
        self._draw_slots()
        self._draw_player_instructions()
        self._draw_takers()

    @staticmethod
    def _reset(table: DataTable[Any], *columns: str) -> int:
        row = table.cursor_row
        table.clear(columns=True)
        table.add_columns(*columns)
        return row

    @staticmethod
    def _restore(table: DataTable[Any], row: int) -> None:
        if table.row_count:
            table.move_cursor(row=min(row, table.row_count - 1))

    def _draw_instructions(self) -> None:
        table = self.query_one("#instructions", DataTable)
        row = self._reset(table, t("ui.tactics.instruction"), t("ui.tactics.setting"))
        table.add_row(t("ui.tactics.ip_formation"), self.tactic.ip_formation, key="ip_formation")
        table.add_row(t("ui.tactics.oop_formation"), self.tactic.oop_formation,
                      key="oop_formation")
        table.add_row(t("ui.tactics.mentality"),
                      self._label(self.options.mentality, self.tactic.mentality),
                      key="mentality")
        phase = None
        for option in self.options.team:
            if option.phase != phase:
                phase = option.phase
                table.add_row(f"[b]{t(f'tactics.phase.{phase}')}[/b]", "", key=f"phase:{phase}")
            table.add_row(f"  {option.label}",
                          self._label(option, self.tactic.setting(option.id)),
                          key=f"team:{option.id}")
        table.add_row(f"[b]{t('tactics.phase.set_pieces')}[/b]", "", key="phase:set_pieces")
        setups = dict(self.tactic.set_pieces.setups)
        for option in self.options.setups:
            table.add_row(f"  {option.label}", self._label(option, setups[option.id]),
                          key=f"setup:{option.id}")
        self._restore(table, row)

    def _draw_slots(self) -> None:
        table = self.query_one("#slots", DataTable)
        row = self._reset(table, t("ui.tactics.slot"), t("ui.tactics.player"),
                          t("ui.tactics.ip_role"), t("ui.tactics.oop_role"))
        names = self._names()
        positions = api.formation_positions(self.tactic.ip_formation)
        roles = {r.id: r for p in ("ip", "oop") for pos in set(positions)
                 for r in api.valid_roles(pos, p)}
        for slot in self.tactic.slots:
            pid = self.players.get(slot.slot)
            cells = []
            for role_id in (slot.ip_role, slot.oop_role):
                label = roles[role_id].label if role_id in roles else role_id
                fit = (f" ({api.role_suitability(self.career, pid, role_id):.0f})"
                       if pid is not None else "")
                cells.append(label + fit)
            table.add_row(positions[slot.slot], names.get(pid or "", "–"), *cells,
                          key=str(slot.slot))
        self._restore(table, row)

    def _locked(self) -> dict[str, str]:
        slot = self.tactic.slots[self.slot]
        roles = {r.id: r for p in ("ip", "oop")
                 for r in api.valid_roles(api.formation_positions(
                     self.tactic.ip_formation)[slot.slot], p)}
        locked: dict[str, str] = {}
        for role_id in (slot.ip_role, slot.oop_role):
            if role_id in roles:
                locked.update(roles[role_id].locked)
        return locked

    def _draw_player_instructions(self) -> None:
        table = self.query_one("#player-instructions", DataTable)
        row = self._reset(table, t("ui.tactics.player_instruction"), t("ui.tactics.setting"))
        chosen = dict(self.tactic.slots[self.slot].instructions)
        locked = self._locked()
        for option in self.options.player:
            if option.id in locked:
                value = f"{self._label(option, locked[option.id])} 🔒 {t('ui.tactics.locked')}"
            else:
                value = self._label(option, chosen.get(option.id, option.default))
            table.add_row(option.label, value, key=option.id)
        self._restore(table, row)

    def _draw_takers(self) -> None:
        table = self.query_one("#takers", DataTable)
        row = self._reset(table, t("ui.tactics.taker"), t("ui.tactics.player"))
        names = self._names()
        labels = dict(zip(self.options.takers, self.options.taker_labels, strict=True))
        for taker, pid in self.tactic.set_pieces.takers:
            table.add_row(labels[taker], names.get(pid or "", t("ui.tactics.auto")), key=taker)
        self._restore(table, row)

    # -- editing -------------------------------------------------------------------------------

    def _message(self, text: str) -> None:
        self.query_one("#tactics-message", Static).update(text)

    @staticmethod
    def _next(values: Any, current: Any) -> Any:
        values = list(values)
        return values[(values.index(current) + 1) % len(values)] if current in values \
            else values[0]

    def _with_team(self, option_id: str, setting: str) -> api.Tactic:
        team = dict(self.tactic.team)
        team[option_id] = setting
        return dataclasses.replace(self.tactic, team=tuple(sorted(team.items())))

    def _key(self, table: DataTable[Any]) -> str:
        return str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "slots" and event.row_key.value is not None:
            slot = int(event.row_key.value)
            if slot != self.slot:
                self.slot = slot
                self._draw_player_instructions()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()  # Enter on any list changes the highlighted setting
        self.action_cycle()

    def action_cycle(self) -> None:
        focused = self.focused
        if not isinstance(focused, DataTable) or focused.row_count == 0:
            return
        self._message("")
        key = self._key(focused)
        if focused.id == "instructions":
            self._cycle_instruction(key)
        elif focused.id == "slots":
            self._cycle_role(int(key), "ip")
        elif focused.id == "player-instructions":
            self._cycle_player_instruction(key)
        elif focused.id == "takers":
            self._cycle_taker(key)
        self._redraw()

    def _cycle_instruction(self, key: str) -> None:
        kind, _, option_id = key.partition(":")
        tactic = self.tactic
        if kind == "ip_formation":
            self._message(t("ui.tactics.formation_from_selection"))
        elif kind == "oop_formation":
            choices = api.suggest_oop_formations(tactic.ip_formation)
            self.tactic = dataclasses.replace(
                tactic, oop_formation=self._next(choices, tactic.oop_formation))
        elif kind == "mentality":
            self.tactic = dataclasses.replace(
                tactic, mentality=self._next(self.options.mentality.settings, tactic.mentality))
        elif kind == "team":
            option = next(o for o in self.options.team if o.id == option_id)
            self.tactic = self._with_team(option_id,
                                          self._next(option.settings, tactic.setting(option_id)))
        elif kind == "setup":
            option = next(o for o in self.options.setups if o.id == option_id)
            setups = dict(tactic.set_pieces.setups)
            setups[option_id] = self._next(option.settings, setups[option_id])
            self.tactic = dataclasses.replace(tactic, set_pieces=dataclasses.replace(
                tactic.set_pieces, setups=tuple(setups.items())))

    def _cycle_role(self, slot_index: int, phase: str) -> None:
        position = api.formation_positions(self.tactic.ip_formation)[slot_index]
        choices = [r.id for r in api.valid_roles(position, phase)]
        slot = self.tactic.slots[slot_index]
        current = slot.ip_role if phase == "ip" else slot.oop_role
        # the core applies the change, including the instructions the new roles lock
        self.tactic = api.set_role(self.tactic, slot.slot, phase, self._next(choices, current))

    def _cycle_player_instruction(self, option_id: str) -> None:
        if option_id in self._locked():
            self._message(t("ui.tactics.locked_refused"))
            return
        option = next(o for o in self.options.player if o.id == option_id)
        slots = list(self.tactic.slots)
        slot = slots[self.slot]
        chosen = dict(slot.instructions)
        setting = self._next(option.settings, chosen.get(option_id, option.default))
        if setting == option.default:
            chosen.pop(option_id, None)
        else:
            chosen[option_id] = setting
        slots[self.slot] = dataclasses.replace(slot, instructions=tuple(sorted(chosen.items())))
        self.tactic = dataclasses.replace(self.tactic, slots=tuple(slots))

    def _cycle_taker(self, taker: str) -> None:
        order = [None, *[self.players[i] for i in sorted(self.players)]]
        takers = dict(self.tactic.set_pieces.takers)
        takers[taker] = self._next(order, takers.get(taker))
        self.tactic = dataclasses.replace(self.tactic, set_pieces=dataclasses.replace(
            self.tactic.set_pieces, takers=tuple(takers.items())))

    def action_cycle_oop(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable) and focused.id == "slots" and focused.row_count:
            self._cycle_role(int(self._key(focused)), "oop")
            self._redraw()

    def action_reset(self) -> None:
        self.tactic = api.default_tactic(self.tactic.ip_formation)
        self._message("")
        self._redraw()

    def action_confirm(self) -> None:
        issues = api.validate_tactic(self.career, self.tactic)
        if issues:
            self._message(t("ui.tactics.errors",
                            problems=", ".join(f"{i.code} {i.path}" for i in issues)))
            return
        if self.live is not None:
            api.live_tactic(self.career, self.live, self.tactic)
        else:
            api.confirm_tactic(self.career, self.tactic)
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class MatchDayScreen(ModalScreen["api.Stop | None"]):
    """The user's match, live (spec 008): the screen drives the clock through the core. Space
    pauses; while paused, S substitutes and X changes the tactic. Enter plays to full time,
    commits the match and goes on to the next stop."""

    BINDINGS = [
        Binding("1", "speed('1')", "Lento"),
        Binding("2", "speed('2')", "Normal"),
        Binding("3", "speed('3')", "Rápido"),
        Binding("4", "instant", "Até o fim"),
        Binding("space", "pause", "Pausar"),
        Binding("s", "subs", "Substituições"),
        Binding("x", "tactics", "Tática"),
        Binding("enter", "close", "Continuar"),
    ]

    STEP_SECONDS = {"1": 7.5, "2": 15.0, "3": 45.0}  # match time per tick (0.25 s)

    def __init__(self, career: api.Career, saves: Path, speed: str = "2") -> None:
        super().__init__()
        self.career = career
        self.saves = saves
        self.session = api.start_live_match(career)
        self.match_id = self.session.match_id
        self.sent = 0
        self.speed = speed
        self.paused = False
        self.timer: Timer | None = None
        self.lines: list[api.FeedLine] = []
        self.stats_shown = False

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[b]{t('ui.match.title')}[/b]", id="match-title")
            yield Static(id="match-clock")
            yield RichLog(id="feed", wrap=True, markup=True)
            yield Static(t("ui.match.live_help"))

    def on_mount(self) -> None:
        self._write_new()
        self._start()

    def _start(self) -> None:
        if self.timer is not None:
            self.timer.stop()
        self.timer = self.set_interval(0.25, self._tick)

    def _stop(self) -> None:
        if self.timer is not None:
            self.timer.stop()
            self.timer = None

    def _tick(self) -> None:
        api.live_advance(self.session, self.STEP_SECONDS[self.speed])
        self._write_new()
        if self.session.match.finished:
            self._stop()
            self._finish()

    def _write_new(self) -> None:
        feed = api.live_feed(self.career, self.session)
        log = self.query_one("#feed", RichLog)
        for line in feed[self.sent:]:
            minute = "" if line.kind == "kickoff" else f"{line.minute}'"
            log.write(f"{minute:>6}  {line.text}")
        self.sent = len(feed)
        self.lines = feed
        state = api.live_state(self.career, self.session)
        clock = f"{state.minute}'  {state.score[0]} x {state.score[1]}"
        if self.paused:
            clock += f"  [b]{t('ui.live.paused')}[/b]"
        self.query_one("#match-clock", Static).update(clock)

    def _finish(self) -> None:
        if self.stats_shown:
            return
        self.stats_shown = True
        log = self.query_one("#feed", RichLog)
        log.write("")
        log.write(f"[b]{t('ui.match.final')}[/b]")
        report = self.session.match.report()
        for key in api.STAT_KEYS:
            home, away = getattr(report.home, key), getattr(report.away, key)
            if key == "possession":
                home, away = f"{home}%", f"{away}%"
            log.write(f"{t(f'stat.{key}'):14}{home!s:>10}{away!s:>10}")

    def action_speed(self, speed: str) -> None:
        self.speed = speed
        if not self.session.match.finished:
            self.paused = False
            self._start()

    def action_pause(self) -> None:
        if self.session.match.finished:
            return
        self.paused = not self.paused
        if self.paused:
            self._stop()
        else:
            self._start()
        self._write_new()

    def action_instant(self) -> None:
        self._stop()
        api.live_advance(self.session, 3 * 60 * 60)
        self._write_new()
        self._finish()

    def action_subs(self) -> None:
        if self.session.match.finished:
            return
        if not self.paused:
            self.action_pause()
        self.app.push_screen(LiveSubsScreen(self.career, self.session),
                             lambda _: self._write_new())

    def action_tactics(self) -> None:
        if self.session.match.finished:
            return
        if not self.paused:
            self.action_pause()
        self.app.push_screen(TacticsScreen(self.career, live=self.session),
                             lambda _: self._write_new())

    def action_close(self) -> None:
        self.action_instant()
        stop = api.finish_live_match(self.career, self.session, self.saves)
        self.dismiss(stop)


class LiveSubsScreen(ModalScreen[None]):
    """Substitutions during a paused live match: pick a player on the pitch and one on the
    bench; the core applies the rules."""

    BINDINGS = [
        Binding("enter", "substitute", "Substituir"),
        Binding("tab", "app.focus_next", "Lista", show=False),
        Binding("escape", "close", "Voltar"),
    ]

    def __init__(self, career: api.Career, session: api.LiveSession) -> None:
        super().__init__()
        self.career = career
        self.session = session

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[b]{t('ui.live.subs')}[/b]")
            with Horizontal():
                yield DataTable(id="live-on", cursor_type="row")
                yield DataTable(id="live-bench", cursor_type="row")
            yield Static(id="live-message")

    def on_mount(self) -> None:
        self._redraw()
        self.query_one("#live-on", DataTable).focus()

    def _redraw(self) -> None:
        state = api.live_state(self.career, self.session)
        on = self.query_one("#live-on", DataTable)
        bench = self.query_one("#live-bench", DataTable)
        for table in (on, bench):
            table.clear(columns=True)
        on.add_columns(t("ui.select.pos"), t("ui.select.player"), t("ui.live.energy"), "")
        bench.add_columns(t("ui.live.bench"))
        for p in state.on_pitch:
            on.add_row(p.position, p.name, f"{p.energy:.0%}", "🟨" if p.yellow else "",
                       key=p.player_id)
        for p in state.bench:
            bench.add_row(p.name, key=p.player_id)
        self.query_one("#live-message", Static).update(
            t("ui.live.subs_left", subs=state.subs_left, windows=state.windows_left))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        self.action_substitute()

    def action_substitute(self) -> None:
        on = self.query_one("#live-on", DataTable)
        bench = self.query_one("#live-bench", DataTable)
        if on.row_count == 0 or bench.row_count == 0:
            return
        off = str(on.coordinate_to_cell_key(on.cursor_coordinate).row_key.value)
        incoming = str(bench.coordinate_to_cell_key(bench.cursor_coordinate).row_key.value)
        try:
            api.live_substitute(self.session, off, incoming)
        except api.LiveMatchError as error:
            self.query_one("#live-message", Static).update(error.message)
            return
        self._redraw()

    def action_close(self) -> None:
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
        Binding("x", "tactics", t("ui.menu.tactics")),
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
                         + f"\n[b]X[/b] {t('ui.menu.tactics')}"
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
            for notice in self.career.notices:
                self.notify(notice, severity="warning", timeout=15)
            self.career.notices.clear()

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

    def action_tactics(self) -> None:
        if self.career is not None:
            self.push_screen(TacticsScreen(self.career))

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
        self.push_screen(MatchDayScreen(career, self.saves), self._after_match)

    def _after_match(self, stop: api.Stop | None) -> None:
        self.refresh_views()
        if stop is not None:
            self._handle_stop(stop)

    def action_quit_game(self) -> None:
        if self.career is not None:
            api.save_career(self.career, self.saves)
        self.exit()
