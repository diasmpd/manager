"""Command-line interface (contracts/cli.md). Calls only the facade, and all text goes
through i18n. Formatting lives here; game rules do not."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from manager_core import api
from manager_core.competition.results import PLACEHOLDER
from manager_core.competition.season import Season, SeasonError, SeasonEvent
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import Position
from manager_core.i18n import t
from manager_core.io.validate import Issue, ValidationReport

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
    """Rebuild the season deterministically (no saves until spec 004) and, for result views,
    replay it up to --date (default: the end of the year)."""
    dataset = _load(args.data)
    if dataset is None:
        return None
    season = api.start_season(dataset, args.ruleset, args.year, args.master_seed)
    if play:
        api.advance_to(season, args.date or date(args.year, 12, 31))
    return season


def _match_line(m: api.MatchView) -> str:
    score, note = "x", ""
    if m.result is not None:
        score = f"{m.result.home_goals} x {m.result.away_goals}"
        if m.result.shootout is not None:
            pens = m.result.shootout.score
            score += f" ({t('season.pens')} {pens[m.home_id]}–{pens[m.away_id]})"
        if m.result.source == PLACEHOLDER:
            note = f" {t('season.provisional')}"
    return (f"  {_fmt_kickoff(m.kickoff)}  {m.home_name} {score} {m.away_name}"
            f"  ({m.venue}){note}")


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
            stage = t(f"season.stage.{m.stage_id}")
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
          t(f"zone.{r.zone.replace(':', '.')}") if r.zone else "",
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
            print(t(f"season.stage.{tie.stage_id}"))
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
    name = season.club_name
    print(f"{t('outcome.champion')}: {name(out.champion)}")
    print(f"{t('outcome.runner_up')}: {name(out.runner_up)}")
    print(f"{t('outcome.semifinalists')}: {', '.join(name(c) for c in out.semifinalists)}")
    for track, winner in out.side_titles.items():
        print(f"{t(f'outcome.{track}')}: {name(winner)}")
    print(f"{t('outcome.relegated')}: {', '.join(name(c) for c in out.relegated)}")
    print(f"{t('outcome.classification')}:")
    for place, club in enumerate(out.final_classification, start=1):
        print(f"  {place:>2}. {name(club)}")
    print(t("season.provisional_note"))
    return EXIT_OK


def _fmt_date(day: date) -> str:
    return f"{t(f'weekday.{day.weekday()}')} {day:%d/%m/%Y}"


def _event_text(season: Season, e: SeasonEvent) -> str:
    names = [season.club_name(c) if c in season.participants else c for c in e.payload]
    return t(f"event.{e.kind}", detail=", ".join(names))


def _add_season_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ruleset", default="mg-modulo-i-2026")
    parser.add_argument("--year", type=int, default=2027)
    parser.add_argument("--master-seed", type=int, default=20261002)
    parser.add_argument("--date", type=date.fromisoformat, default=None)


def _sub_date(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """--date also accepted after the subcommand, without overriding one given before it."""
    parser.add_argument("--date", type=date.fromisoformat, default=argparse.SUPPRESS)
    return parser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manager_core", description=t("cli.description"))
    parser.add_argument("--data", type=Path, default=_default_data_dir())
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
    return code
