"""Command-line interface (contracts/cli.md). Calls only the facade, and all text goes
through i18n. Formatting lives here; game rules do not."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from manager_core import api
from manager_core.career.career import Career, Stop
from manager_core.career.store import SaveError
from manager_core.competition.calendar import CalendarDay
from manager_core.competition.results import PLACEHOLDER
from manager_core.competition.rules import RulesetError, RulesetReport
from manager_core.competition.season import Season, SeasonError, SeasonEvent
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.i18n import t
from manager_core.io.validate import Issue, ValidationReport
from manager_core.quicksim.report import SideStats, keeper_at_end
from manager_core.quicksim.shootout import kick_takers

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3


def _default_data_dir() -> Path:
    repo = Path(__file__).resolve().parents[3]
    candidate = repo / "data" / "sample"
    return candidate if candidate.is_dir() else Path.cwd() / "data" / "sample"


# ---- rendering helpers ---------------------------------------------------------------------


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    cells = [[str(c) for c in headers]] + [[str(c) for c in r] for r in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    for n, row in enumerate(cells):
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if n == 0:
            print("  ".join("-" * w for w in widths))


def _pos(position: Position) -> str:
    return t(f"pos.{position.value}")


def _suit(milli: int) -> str:
    return f"{milli / 1000:.1f}"


def _issue_line(issue: Issue) -> str:
    parts = [t("cli.row", row=issue.row) if issue.row else ""]
    if issue.record_id:
        parts.append(issue.record_id)
    if issue.field:
        value = f" = {issue.value!r}" if issue.value not in (None, "") else ""
        parts.append(f"{issue.field}{value}")
    location = " · ".join(p for p in parts if p)
    prefix = f"    [{issue.code}]"
    return f"{prefix} {location}: {issue.message}" if location else f"{prefix} {issue.message}"


def _print_report(report: ValidationReport) -> None:
    for title, issues in ((t("cli.errors"), report.errors), (t("cli.warnings"), report.warnings)):
        if not issues:
            continue
        print(title)
        current_file = None
        for issue in issues:
            if issue.file != current_file:
                current_file = issue.file
                print(f"  {issue.file}")
            print(_issue_line(issue))
    key = "cli.summary.valid" if report.ok else "cli.summary.invalid"
    print(t(key, errors=len(report.errors), warnings=len(report.warnings)))


def _load(path: Path) -> Dataset | None:
    result = api.load_dataset(path)
    if result.dataset is None:
        print(t("cli.load_failed", path=path), file=sys.stderr)
        _print_report(result.report)
    return result.dataset


# ---- commands ------------------------------------------------------------------------------


def _cmd_data_validate(args: argparse.Namespace) -> int:
    report = api.validate_dataset(Path(args.dir))
    _print_report(report)
    return EXIT_OK if report.ok else EXIT_INVALID


def _cmd_data_export(args: argparse.Namespace) -> int:
    dataset = _load(Path(args.src))
    if dataset is None:
        return EXIT_INVALID
    summary = api.export_dataset(dataset, Path(args.dst))
    print(t("cli.summary.exported", path=summary.path, clubs=summary.clubs,
            players=summary.players, flags=sum(summary.flags.values())))
    for flag, count in summary.flags.items():
        print(f"  {flag}: {count}")
    return EXIT_OK


def _cmd_sample_generate(args: argparse.Namespace) -> int:
    dataset = api.generate_sample(args.seed)
    out = Path(args.out) if args.out else _default_data_dir()
    summary = api.export_dataset(dataset, out)
    print(t("cli.summary.generated", path=out, clubs=summary.clubs, players=summary.players,
            seed=args.seed))
    return EXIT_OK


def _cmd_club_list(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    rows = [
        [c.id, c.name, c.abbreviation, f"{c.city}/{c.state or '-'}", c.reputation, c.squad_size,
         c.average_ca]
        for c in api.list_clubs(dataset)
    ]
    _print_table(
        [t("cli.col.id"), t("cli.col.name"), t("cli.col.abbr"), t("cli.col.city"),
         t("cli.col.reputation"), t("cli.col.squad_size"), t("cli.col.avg_ca")],
        rows,
    )
    return EXIT_OK


def _cmd_club_squad(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    entries = api.squad(dataset, args.club_id, sort=args.sort)
    rows = [
        [e.shirt_number or "", e.label, e.age, _pos(e.best_position), t(f"band.{e.band.value}"),
         _suit(e.suitability_milli), e.current_ability, e.player_id]
        for e in entries
    ]
    _print_table(
        [t("cli.col.number"), t("cli.col.player"), t("cli.col.age"), t("cli.col.position"),
         t("cli.col.band"), t("cli.col.suitability"), t("cli.col.ca"), t("cli.col.id")],
        rows,
    )
    return EXIT_OK


def _cmd_player_show(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    p = api.player_profile(dataset, args.player_id, include_hidden=args.hidden)
    club = f"{p.club_name} (#{p.shirt_number})" if p.club_name else t("cli.profile.free_agent")
    print(f"{p.display_name} — {p.full_name}  [{p.player_id}]")
    print(f"  {t('cli.profile.club')}: {club}")
    print(f"  {t('cli.profile.born')}: {p.date_of_birth.isoformat()} "
          f"({t('cli.profile.age', age=p.age)})")
    print(f"  {t('cli.profile.nationality')}: {', '.join(p.nationalities)}")
    print(f"  {t('cli.profile.height_weight')}: {p.height_cm} cm / {p.weight_kg} kg")
    print(f"  {t('cli.profile.feet')}: {p.left_foot} / {p.right_foot}")
    positions = ", ".join(
        f"{_pos(e.position)} {t(f'band.{e.band.value}')} ({e.value})" for e in p.positions
    )
    print(f"  {t('cli.profile.positions')}: {positions}")
    print(f"  {t('cli.profile.best')}: {_pos(p.best_position)}")
    print(f"  {t('cli.ca')}: {p.current_ability}")
    if p.potential_ability is not None:
        print(f"  {t('cli.pa')}: {p.potential_ability}")
    print()
    groups = list(p.attributes) + ([p.hidden] if p.hidden else [])
    columns = []
    for g in groups:
        names = [t(f"attr.{n}") for n, _ in g.values]
        pad = max(len(name) for name in names)
        columns.append(
            [t(f"group.{g.group.value}").upper()]
            + [f"{name.ljust(pad)} {v:>2}" for name, (_, v) in zip(names, g.values, strict=True)]
        )
    width = max(len(line) for col in columns for line in col) + 3
    for i in range(max(len(c) for c in columns)):
        print("".join((c[i] if i < len(c) else "").ljust(width) for c in columns).rstrip())
    return EXIT_OK


def _parse_position(code: str) -> Position:
    try:
        return Position(code.upper())
    except ValueError:
        raise api.NotFoundError("position", code) from None


def _cmd_position_rank(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    position = _parse_position(args.position)
    rows = [
        [r.label, t(f"band.{r.band.value}"), _suit(r.suitability_milli), r.player_id]
        for r in api.rank_for_position(dataset, args.club_id, position)
    ]
    _print_table(
        [t("cli.col.player"), t("cli.col.band"), t("cli.col.suitability"), t("cli.col.id")], rows
    )
    return EXIT_OK


def _cmd_lineup_suggest(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    result = api.suggest_lineup(dataset, args.club_id, formation=args.formation)
    labels = {e.player_id: e.label for e in api.squad(dataset, args.club_id)}
    rows = [
        [_pos(a.position), labels[a.player_id], _suit(a.suitability_milli), a.player_id]
        for a in result.assignments
    ]
    print(t("cli.lineup.title", formation=result.formation))
    _print_table(
        [t("cli.col.slot"), t("cli.col.player"), t("cli.col.suitability"), t("cli.col.id")], rows
    )
    print(t("cli.lineup.total", total=_suit(result.total_milli)))
    for flag in result.flags:
        print(f"  ! {t(f'cli.lineup.flag.{flag}')}")
    return EXIT_OK


def _cmd_formation_list(args: argparse.Namespace) -> int:
    for f in api.list_formations():
        print(f"{f.name:<8} " + " ".join(_pos(p) for p in f.positions))
    return EXIT_OK


# ---- season (spec 002) ----------------------------------------------------------------------


def _fmt_kickoff(when: datetime) -> str:
    return f"{t(f'weekday.{when.weekday()}')} {when:%d/%m/%Y %H:%M}"


def _season(args: argparse.Namespace, play: bool = False) -> Season | None:
    """The career's season (--career), or a season rebuilt deterministically from the seed
    and, for result views, replayed up to --date (default: the end of the year)."""
    if getattr(args, "career", None):
        return api.load_career(args.saves, args.career).season
    dataset = _load(args.data)
    if dataset is None:
        return None
    participants = args.participants.split(",") if args.participants else None
    season = api.start_season(dataset, args.ruleset, args.year, args.master_seed, participants)
    if play:
        api.advance_to(season, args.date or date(args.year, 12, 31))
    return season


def _match_line(m: api.MatchView, *, with_date: bool = True) -> str:
    score, note = "x", ""
    if m.result is not None:
        score = f"{m.result.home_goals} x {m.result.away_goals}"
        if m.result.shootout is not None:
            pens = m.result.shootout.score
            score += f" ({t('season.pens')} {pens[m.home_id]}–{pens[m.away_id]})"
        if m.result.source == PLACEHOLDER:
            note = f" {t('season.provisional')}"
    when = _fmt_kickoff(m.kickoff) if with_date else f"{m.kickoff:%H:%M}"
    return (f"  {when}  {m.home_name} {score} {m.away_name}"
            f"  ({m.venue}){note}  [{m.id}]")


def _cmd_season_groups(args: argparse.Namespace) -> int:
    season = _season(args)
    if season is None:
        return EXIT_INVALID
    for g in api.season_groups(season):
        print(t("season.group", label=g.label))
        for name in g.club_names:
            print(f"  {name}")
    return EXIT_OK


def _cmd_season_fixtures(args: argparse.Namespace) -> int:
    season = _season(args)
    if season is None:
        return EXIT_INVALID
    matches = api.season_fixtures(season, club_id=args.club, round=args.round)
    current: tuple[str, int] | None = None
    for m in matches:
        key = (m.stage_id, m.round)
        if args.club is None and key != current:
            current = key
            stage = season.ruleset.stage_name(m.stage_id)
            print(f"{stage} – {t('season.round', round=m.round)}")
        print(_match_line(m))
    return EXIT_OK


def _cmd_season_table(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    rows = api.season_table(season, args.group)
    title = t("season.group", label=args.group) if args.group else t("season.overall")
    print(title)
    _print_table(
        [t(f"table.{k}") for k in ("pos", "club", "p", "w", "d", "l", "gf", "ga", "gd", "pts",
                                   "zone", "decided_by")],
        [[r.place, season.club_name(r.club_id), r.played, r.won, r.drawn, r.lost, r.goals_for,
          r.goals_against, r.goal_difference, r.points,
          _zone_text(season, r.zone),
          # only show real tie-breaks (clubs level on points)
          t(f"criterion.{r.decided_by}") if r.decided_by not in (None, "points") else ""]
         for r in rows],
    )
    return EXIT_OK


def _cmd_season_bracket(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    current = None
    for tie in api.season_bracket(season):
        if tie.stage_id != current:
            current = tie.stage_id
            print(season.ruleset.stage_name(tie.stage_id))
        winner = ""
        if tie.winner_id:
            name = tie.high_name if tie.winner_id == tie.high_id else tie.low_name
            winner = f"  -> {name} ({t(f'tie.{tie.decided_by}')})"
        print(f" {tie.high_name} x {tie.low_name}{winner}")
        for leg in tie.legs:
            print(f"  {_match_line(leg)}")
    return EXIT_OK


def _cmd_season_day(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    view = api.season_day(season, args.date or season.current_date)
    print(_fmt_date(view.day))
    for m in view.matches:
        print(_match_line(m))
    for e in view.events:
        print(f"  * {_event_text(season, e)}")
    return EXIT_OK


def _cmd_season_outcomes(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    out = api.season_outcomes(season)
    if out is None:
        print(t("outcome.not_finished", date=_fmt_date(season.current_date)))
        return EXIT_OK
    name, rules = season.club_name, season.ruleset
    print(f"{rules.track_title('main')}: {name(out.champion)}")
    print(f"{t('outcome.runner_up')}: {name(out.runner_up)}")
    first = rules.stage_name(rules.first_stage_of("main").id)
    entrants = ", ".join(name(c) for c in out.main_entrants)
    print(f"{t('outcome.qualified', stage=first)}: {entrants}")
    for track, winner in out.side_titles.items():
        print(f"{rules.track_title(track)}: {name(winner)}")
    if out.relegated:
        print(f"{t('outcome.relegated')}: {', '.join(name(c) for c in out.relegated)}")
    print(f"{t('outcome.classification')}:")
    for place, club in enumerate(out.final_classification, start=1):
        print(f"  {place:>2}. {name(club)}")
    if any(r.source == PLACEHOLDER for r in season.results.values()):
        print(t("season.provisional_note"))
    return EXIT_OK


def _cmd_season_calendar(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    days = api.season_calendar(season, args.month)
    if args.month is None:
        for month in range(1, 13):
            _print_month_summary([d for d in days if d.day.month == month], month)
        return EXIT_OK
    print(f"{t(f'month.{args.month}').capitalize()} {season.year}")
    for d in days:
        windows = ", ".join(dict.fromkeys(w.name for w in d.windows))
        print(f"{_fmt_date(d.day)}{f'  [{windows}]' if windows else ''}")
        for match_id in d.match_ids:
            print(f"  {_match_line(api.match_view(season, match_id), with_date=False)}")
        for stage_id in d.reserved_stages:
            print(f"    {t('calendar.reserved', stage=season.ruleset.stage_name(stage_id))}")
        for e in d.events:
            print(f"    * {_event_text(season, e)}")
    return EXIT_OK


def _print_month_summary(days: Sequence[CalendarDay], month: int) -> None:
    matches = sum(len(d.match_ids) for d in days)
    match_days = sum(1 for d in days if d.match_ids)
    line = t("calendar.month_summary", month=t(f"month.{month}").capitalize(), matches=matches,
             days=match_days)
    spans: dict[str, list[date]] = {}  # window name -> its days in this month
    for d in days:
        for w in d.windows:
            spans.setdefault(w.name, []).append(d.day)
    if spans:
        parts = [f"{name} {_fmt_span(ds)}" for name, ds in spans.items()]
        line += f"; {t('calendar.windows', windows='; '.join(parts))}"
    print(line)


def _fmt_span(days: Sequence[date]) -> str:
    """Contiguous runs of days, e.g. '06/02–10/02'."""
    runs: list[tuple[date, date]] = []
    for d in sorted(days):
        if runs and (d - runs[-1][1]).days == 1:
            runs[-1] = (runs[-1][0], d)
        else:
            runs.append((d, d))
    return ", ".join(f"{a:%d/%m}" if a == b else f"{a:%d/%m}–{b:%d/%m}" for a, b in runs)


def _cmd_season_match(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    view = api.match_report(season, args.match_id)
    m = view.match
    print(_match_line(m).strip())
    report = view.report
    if report is None:
        if m.result is None:
            print(t("match.not_played"))
        return EXIT_OK
    names = {pid: season.dataset.player(pid).display_name
             for lineup in (report.home_lineup, report.away_lineup)
             for pid in (*[p for _, p in lineup.starters], *lineup.bench)}
    stat_keys = ("shots", "shots_on_target", "xg", "possession", "corners", "fouls",
                 "yellows", "reds")
    _print_table(["", m.home_name, m.away_name],
                 [[t(f"stat.{k}"), _stat(report.home, k), _stat(report.away, k)]
                  for k in stat_keys])
    goals = [e for e in report.events if e.kind in ("goal", "own_goal", "penalty_goal")]
    if goals:
        print(t("match.goals"))
        for e in goals:
            club = m.home_name if e.side == "home" else m.away_name
            note = {"own_goal": f" {t('match.own_goal')}",
                    "penalty_goal": f" {t('match.penalty')}"}.get(e.kind, "")
            assist = (f" ({t('match.assist', name=names[e.other_player_id])})"
                      if e.other_player_id else "")
            print(f"  {e.minute!s:>5}'  {names[e.player_id]}{note}{assist} – {club}")
    others = [e for e in report.events if e.kind not in ("goal", "own_goal", "penalty_goal")]
    for title, kinds in (("match.cards", ("yellow", "second_yellow", "red", "penalty_miss")),
                         ("match.subs", ("sub",))):
        chosen = [e for e in others if e.kind in kinds]
        if not chosen:
            continue
        print(t(title))
        for e in chosen:
            club = m.home_name if e.side == "home" else m.away_name
            if e.kind == "sub":
                text = t("event.sub", out=names[e.player_id], inn=names[e.other_player_id or ""])
            else:
                text = f"{names[e.player_id]}: {t(f'event.{e.kind}')}"
            print(f"  {e.minute!s:>5}'  {text} – {club}")
    shootout = m.result.shootout if m.result else None
    if shootout is not None:
        print(t("match.shootout"))
        players = season.dataset.player
        first = [players(p) for p in sorted(report.home_finishers)]
        second = [players(p) for p in sorted(report.away_finishers)]
        keepers = [keeper_at_end(report, side) for side in ("home", "away")]
        takers = kick_takers(shootout, first, players(keepers[0]) if keepers[0] else None,
                             second, players(keepers[1]) if keepers[1] else None)
        for (club, scored), taker in zip(shootout.kicks, takers, strict=True):
            mark = t("match.scored") if scored else t("match.missed")
            print(f"  {season.club_name(club)}: {names[taker]} – {mark}")
    for lineup in (report.home_lineup, report.away_lineup):
        if "no_goalkeeper" in lineup.flags:
            print(t("match.flag.no_goalkeeper", club=season.club_name(lineup.club_id)))
    return EXIT_OK


def _stat(stats: SideStats, key: str) -> str:
    value = getattr(stats, key)
    if key == "possession":
        return f"{value}%"
    if key == "xg":
        return f"{value:.2f}"
    return str(value)


def _cmd_season_scorers(args: argparse.Namespace) -> int:
    season = _season(args, play=True)
    if season is None:
        return EXIT_INVALID
    rows = api.season_scorers(season, args.limit)
    _print_table([t(f"scorers.{k}") for k in ("pos", "player", "club", "goals", "penalties",
                                              "assists")],
                 [[i, r.player_name, r.club_name, r.goals, r.penalties, r.assists]
                  for i, r in enumerate(rows, start=1)])
    return EXIT_OK


def _cmd_calibrate(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    report = api.run_calibration(dataset, args.gate, args.baseline)
    print(t("calibration.title", gate=args.gate))
    with_before = args.baseline is not None
    headers = ["metric", "value", *(["before"] if with_before else []), "target", "band",
               "verdict", "source"]

    def fmt(value: float | None, unit: str) -> str:
        if value is None:
            return "–"
        return f"{value * 100:.1f}%" if unit == "ratio" else f"{value:.2f}"

    rows = []
    for r in report.results:
        target = r.target
        band = f"{fmt(target.low, target.unit)}–{fmt(target.high, target.unit)}"
        rows.append([t(f"metric.{target.id}"), fmt(r.value, target.unit),
                     *([fmt(r.before, target.unit)] if with_before else []),
                     fmt(target.target, target.unit), band, t(f"calibration.{r.verdict}"),
                     target.source])
    _print_table([t(f"calibration.{h}") for h in headers], rows)
    print(t("calibration.matches", league=report.league_matches, state=report.state_matches))
    if report.caution is not None:
        c = report.caution
        print(t("calibration.caution", on=f"{c.second_yellow_rate_on:.3f}",
                off=f"{c.second_yellow_rate_off:.3f}", cost_on=f"{c.conceded_on:.3f}",
                cost_off=f"{c.conceded_off:.3f}"))
    print(t("calibration.versions", core=report.core_version, python=report.python_version,
            model=report.model_version, hash=report.params_hash))
    if args.write is not None:
        args.write.write_text(report.to_json(), "utf-8")
    if report.passed:
        print(t("calibration.passed"))
        return EXIT_OK
    print(t("calibration.failed", metrics=", ".join(report.failures)))
    return EXIT_INVALID


def _default_saves_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "saves"


def _print_stop(career: Career, stop: Stop) -> None:
    season = career.season
    if stop.kind == "user_match" and stop.match_id:
        print(t("career.stop.user_match"))
        print(_match_line(api.match_view(season, stop.match_id)))
    elif stop.kind == "event":
        print(t("career.stop.event", date=_fmt_date(stop.day)))
        for e in stop.events:
            print(f"  * {_event_text(season, e)}")
    else:
        out = api.season_outcomes(season)
        print(t("career.stop.season_end", year=season.year))
        if out is not None:
            print(f"  {season.ruleset.track_title('main')}: {season.club_name(out.champion)}")
            order = out.final_classification
            if career.user_club_id in order:
                place = order.index(career.user_club_id) + 1
                print("  " + t("career.user_place", club=season.club_name(career.user_club_id),
                               place=place))
            relegated = ", ".join(season.club_name(c) for c in out.relegated)
            print(f"  {t('outcome.relegated')}: {relegated}")
        print("  " + t("career.next_season_hint"))


def _cmd_career_new(args: argparse.Namespace) -> int:
    dataset = _load(args.data)
    if dataset is None:
        return EXIT_INVALID
    career = api.new_career(dataset, args.name, args.club, args.seed)
    api.save_career(career, args.saves)
    season = career.season
    print(t("career.created", name=career.name, club=season.club_name(career.user_club_id),
            year=season.year))
    for g in api.season_groups(season):
        print(f"  {t('season.group', label=g.label)}: {', '.join(g.club_names)}")
    status = api.career_status(career)
    if status.next_match is not None:
        print(t("career.next_match"))
        print(_match_line(status.next_match))
    return EXIT_OK


def _cmd_career_list(args: argparse.Namespace) -> int:
    _print_table([t(f"career.col.{k}") for k in ("name", "club", "date", "season", "saved")],
                 [[s.name, s.user_club_id, _fmt_date(s.current_date), s.year, s.saved_at]
                  for s in api.list_saves(args.saves)])
    return EXIT_OK


def _cmd_career_status(args: argparse.Namespace) -> int:
    career = api.load_career(args.saves, args.name)
    status = api.career_status(career)
    print(t("career.status", name=status.name, club=status.club_name,
            date=_fmt_date(status.current_date), year=status.year))
    if status.position is not None:
        print("  " + t("career.position", place=status.position))
    if status.next_match is not None:
        print("  " + t("career.next_match"))
        print("  " + _match_line(status.next_match))
    if status.suspended:
        print("  " + t("career.suspended"))
        for s in status.suspended:
            print(f"    {s.player_name} ({t('career.matches_left', n=s.matches)})")
    else:
        print("  " + t("career.no_suspensions"))
    return EXIT_OK


def _cmd_career_continue(args: argparse.Namespace) -> int:
    career = api.load_career(args.saves, args.name)
    stop = api.continue_career(career, args.saves, to_season_end=args.to_season_end)
    _print_stop(career, stop)
    return EXIT_OK


def _cmd_career_save(args: argparse.Namespace) -> int:
    career = api.load_career(args.saves, args.name)
    api.save_career(career, args.saves, args.as_name)
    print(t("career.saved_as", name=args.as_name))
    return EXIT_OK


def _cmd_career_delete(args: argparse.Namespace) -> int:
    api.delete_save(args.saves, args.name)
    print(t("career.deleted", name=args.name))
    return EXIT_OK


def _cmd_career_history(args: argparse.Namespace) -> int:
    career = api.load_career(args.saves, args.name)
    world = career.world

    def name(club_id: str) -> str:
        return world.club(club_id).short_name if club_id in world.clubs else club_id

    _print_table([t(f"career.hist.{k}") for k in ("year", "champion", "place", "relegated",
                                                   "promoted")],
                 [[r.year, name(r.champion), r.user_place or "-",
                   ", ".join(name(c) for c in r.relegated),
                   ", ".join(name(c) for c in r.promoted)]
                  for r in api.career_history(career)])
    return EXIT_OK


def _print_ruleset_report(report: RulesetReport) -> None:
    for issue in report.issues:
        print(f"{issue.code}  {issue.message}")


def _cmd_season_rules(args: argparse.Namespace) -> int:
    if args.validate is not None:
        report = api.validate_ruleset(args.validate)
        if report.ok:
            print(t("rules.ok", path=args.validate))
            return EXIT_OK
        _print_ruleset_report(report)
        print(t("rules.invalid", count=len(report.issues)))
        return EXIT_INVALID
    _print_table(
        [t(f"rules.{k}") for k in ("id", "name", "state", "valid")],
        [[r.id, r.name, r.state, f"{r.valid_from}–{r.valid_to or ''}"]
         for r in api.list_rulesets()],
    )
    return EXIT_OK


def _fmt_date(day: date) -> str:
    return f"{t(f'weekday.{day.weekday()}')} {day:%d/%m/%Y}"


def _event_text(season: Season, e: SeasonEvent) -> str:
    stage_ids = {st.id for st in season.ruleset.stages}
    tracks = set(season.ruleset.tracks())

    def label(item: str) -> str:
        if item in season.participants:
            return season.club_name(item)
        if item in stage_ids:
            return season.ruleset.stage_name(item)
        if item in tracks:
            return season.ruleset.track_title(item)
        return item

    return t(f"event.{e.kind}", detail=", ".join(label(p) for p in e.payload))


def _zone_text(season: Season, zone: str | None) -> str:
    if zone is None:
        return ""
    if zone.startswith("track:"):
        track = zone.removeprefix("track:")
        if track == "main":
            return season.ruleset.stage_name(season.ruleset.first_stage_of(track).id)
        return season.ruleset.track_title(track)
    return t(f"zone.{zone}")


def _add_season_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ruleset", default=api.DEFAULT_RULESET)
    parser.add_argument("--year", type=int, default=2027)
    parser.add_argument("--master-seed", type=int, default=20261002)
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--participants", help="club ids separated by commas")


def _sub_date(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """--date also accepted after the subcommand, without overriding one given before it."""
    parser.add_argument("--date", type=date.fromisoformat, default=argparse.SUPPRESS)
    return parser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manager_core", description=t("cli.description"))
    parser.add_argument("--data", type=Path, default=_default_data_dir())
    parser.add_argument("--saves", type=Path, default=_default_saves_dir())
    groups = parser.add_subparsers(dest="group", required=True)

    data = groups.add_parser("data").add_subparsers(dest="command", required=True)
    cmd = data.add_parser("validate")
    cmd.add_argument("dir")
    cmd.set_defaults(func=_cmd_data_validate)
    cmd = data.add_parser("export")
    cmd.add_argument("src")
    cmd.add_argument("dst")
    cmd.set_defaults(func=_cmd_data_export)

    sample = groups.add_parser("sample").add_subparsers(dest="command", required=True)
    cmd = sample.add_parser("generate")
    cmd.add_argument("--seed", type=int, default=api.DEFAULT_SEED)
    cmd.add_argument("--out")
    cmd.set_defaults(func=_cmd_sample_generate)

    club = groups.add_parser("club").add_subparsers(dest="command", required=True)
    club.add_parser("list").set_defaults(func=_cmd_club_list)
    cmd = club.add_parser("squad")
    cmd.add_argument("club_id")
    cmd.add_argument("--sort", choices=["position", "ca", "age", "number"], default="position")
    cmd.set_defaults(func=_cmd_club_squad)

    player = groups.add_parser("player").add_subparsers(dest="command", required=True)
    cmd = player.add_parser("show")
    cmd.add_argument("player_id")
    cmd.add_argument("--hidden", action="store_true")
    cmd.set_defaults(func=_cmd_player_show)

    position = groups.add_parser("position").add_subparsers(dest="command", required=True)
    cmd = position.add_parser("rank")
    cmd.add_argument("club_id")
    cmd.add_argument("position")
    cmd.set_defaults(func=_cmd_position_rank)

    lineup = groups.add_parser("lineup").add_subparsers(dest="command", required=True)
    cmd = lineup.add_parser("suggest")
    cmd.add_argument("club_id")
    cmd.add_argument("--formation", default="4-4-2")
    cmd.set_defaults(func=_cmd_lineup_suggest)

    formation = groups.add_parser("formation").add_subparsers(dest="command", required=True)
    formation.add_parser("list").set_defaults(func=_cmd_formation_list)

    season = groups.add_parser("season")
    _add_season_options(season)
    season.add_argument("--career", help="show this career's current season")
    season_cmds = season.add_subparsers(dest="command", required=True)
    _sub_date(season_cmds.add_parser("groups")).set_defaults(func=_cmd_season_groups)
    cmd = _sub_date(season_cmds.add_parser("fixtures"))
    cmd.add_argument("--club")
    cmd.add_argument("--round", type=int)
    cmd.set_defaults(func=_cmd_season_fixtures)
    cmd = _sub_date(season_cmds.add_parser("table"))
    cmd.add_argument("--group")
    cmd.add_argument("--overall", action="store_true")
    cmd.set_defaults(func=_cmd_season_table)
    _sub_date(season_cmds.add_parser("bracket")).set_defaults(func=_cmd_season_bracket)
    _sub_date(season_cmds.add_parser("day")).set_defaults(func=_cmd_season_day)
    _sub_date(season_cmds.add_parser("outcomes")).set_defaults(func=_cmd_season_outcomes)
    cmd = _sub_date(season_cmds.add_parser("calendar"))
    cmd.add_argument("--month", type=int)
    cmd.set_defaults(func=_cmd_season_calendar)
    cmd = _sub_date(season_cmds.add_parser("match"))
    cmd.add_argument("match_id")
    cmd.set_defaults(func=_cmd_season_match)
    cmd = _sub_date(season_cmds.add_parser("scorers"))
    cmd.add_argument("--limit", type=int, default=10)
    cmd.set_defaults(func=_cmd_season_scorers)
    cmd = season_cmds.add_parser("rules")
    cmd.add_argument("--validate", type=Path, metavar="PATH")
    cmd.set_defaults(func=_cmd_season_rules)
    career = groups.add_parser("career").add_subparsers(dest="command", required=True)
    cmd = career.add_parser("new")
    cmd.add_argument("name")
    cmd.add_argument("--club", required=True)
    cmd.add_argument("--seed", type=int)
    cmd.set_defaults(func=_cmd_career_new)
    career.add_parser("list").set_defaults(func=_cmd_career_list)
    for command, func in (("status", _cmd_career_status), ("delete", _cmd_career_delete),
                          ("history", _cmd_career_history)):
        cmd = career.add_parser(command)
        cmd.add_argument("name")
        cmd.set_defaults(func=func)
    cmd = career.add_parser("continue")
    cmd.add_argument("name")
    cmd.add_argument("--to-season-end", action="store_true")
    cmd.set_defaults(func=_cmd_career_continue)
    cmd = career.add_parser("save")
    cmd.add_argument("name")
    cmd.add_argument("--as", dest="as_name", required=True)
    cmd.set_defaults(func=_cmd_career_save)

    cmd = groups.add_parser("calibrate")
    cmd.add_argument("--gate", choices=["pr", "milestone"], default="pr")
    cmd.add_argument("--baseline", type=Path)
    cmd.add_argument("--write", type=Path)
    cmd.set_defaults(func=_cmd_calibrate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    try:
        code: int = args.func(args)
    except api.NotFoundError as exc:
        print(t(f"cli.not_found.{exc.kind}", id=exc.id), file=sys.stderr)
        return EXIT_NOT_FOUND
    except SeasonError as exc:
        print(exc.message, file=sys.stderr)
        return EXIT_INVALID
    except SaveError as exc:
        print(exc.message, file=sys.stderr)
        return EXIT_INVALID
    except RulesetError as exc:
        for issue in exc.report.issues:
            print(f"{issue.code}  {issue.message}", file=sys.stderr)
        return EXIT_INVALID
    return code
