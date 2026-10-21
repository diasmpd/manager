"""The assistant's suggestions (spec 010 T003-T010), on the fictional sample."""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from pathlib import Path

import pytest

from manager_core import api
from manager_core.career import assistant
from manager_core.career.career import Career
from manager_core.career.discipline import YELLOWS_PER_BAN, Discipline
from manager_core.domain.attributes import HIDDEN_ATTRIBUTES
from manager_core.domain.dataset import Dataset
from manager_core.domain.positions import NATURAL_THRESHOLD, Position
from manager_core.tactics import ai

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def world() -> Dataset:
    dataset = api.load_dataset(SAMPLE).dataset
    assert dataset is not None
    return dataset


def _career(world: Dataset, club: str = "alvorada", seed: int = 3) -> Career:
    return api.new_career(world, "assistente", club, master_seed=seed)


def _play_until_next_user_match(career: Career, tmp: Path, matches: int = 1) -> None:
    for _ in range(matches):
        stop = api.continue_career(career, tmp)
        while stop.kind != "user_match":
            stop = api.continue_career(career, tmp)
        api.continue_career(career, tmp)  # plays it


# ---- US1: the opposition report --------------------------------------------------------------


def test_the_report_reads_the_opponent_as_the_ai_plays_it(world: Dataset) -> None:
    career = _career(world)
    match = assistant.next_user_match(career)
    assert match is not None
    report = assistant.opposition_report(career, match.id)
    opponent = match.away_id if match.home_id == "alvorada" else match.home_id
    assert report.opponent_id == opponent
    assert report.style == career.live_provider.styles()[opponent]
    assert report.formation == career.live_provider.team_sheet(opponent).formation.name
    assert report.band in ("favourite", "even", "underdog")
    assert len(report.key_players) == assistant.params()["key_players"]
    assert report.form == () and "Ainda não jogaram" in report.text  # the first round
    assert report.opponent_name in report.text and report.style_label in report.text


def test_form_and_scorers_count_only_the_matches_before_the_day(world: Dataset,
                                                                 tmp_path: Path) -> None:
    career = _career(world)
    _play_until_next_user_match(career, tmp_path, matches=3)
    match = assistant.next_user_match(career)
    assert match is not None
    report = assistant.opposition_report(career, match.id)
    assert 1 <= len(report.form) <= assistant.params()["form_matches"]
    assert set(report.form) <= {"V", "E", "D"}
    first_day = min(m.kickoff.date() for m in career.season.sorted_matches())
    early = assistant.opposition_report(career, match.id, as_of=first_day)
    assert early.form == () and early.top_scorers == ()
    total = sum(g for _, g in report.top_scorers)
    assert total >= sum(g for _, g in early.top_scorers)


def test_a_report_for_an_earlier_day_leaves_suspensions_out(world: Dataset) -> None:
    career = _career(world)
    match = assistant.next_user_match(career)
    assert match is not None
    ledger = career.season.discipline
    assert isinstance(ledger, Discipline)
    opponent = match.away_id if match.home_id == "alvorada" else match.home_id
    banned = next(p.id for p in world.squad(opponent))
    ledger._bans[banned] = 1
    assert world.player(banned).display_name in assistant.opposition_report(
        career, match.id).suspended
    assert assistant.opposition_report(career, match.id, with_suspensions=False).suspended == ()


# ---- US2: the selection ----------------------------------------------------------------------


def test_one_booking_from_a_ban(world: Dataset) -> None:
    career = _career(world)
    selection = api.propose_selection(career)
    pid = selection.starters[3][1]
    ledger = career.season.discipline
    assert isinstance(ledger, Discipline)
    ledger._yellows[pid] = YELLOWS_PER_BAN - 1
    advice = assistant.selection_advice(career, selection)
    hung = [a for a in advice if a.kind == "one_from_ban"]
    assert len(hung) == 1 and world.player(pid).display_name in hung[0].text
    assert hung[0].action is None and hung[0].severity == assistant.WARNING


def _slots(selection: api.Selection) -> list[Position]:
    return [Position(p) for p in api.formation_positions(selection.formation)]


def test_out_of_position_with_a_natural_swap_that_clears_it(world: Dataset) -> None:
    career = _career(world)
    selection = api.propose_selection(career)
    positions = _slots(selection)
    striker_slot = next(i for i, pos in enumerate(positions) if pos is Position.ST)
    keeper = next(pid for i, pid in selection.starters if positions[i] is Position.GK)
    others = [p for p in world.squad("alvorada") if p.id not in selection.players
              and p.positions[Position.ST] < NATURAL_THRESHOLD
              and p.positions[Position.GK] < NATURAL_THRESHOLD]
    misplaced = api.swap_in_selection(career, selection, striker_slot, others[0].id)
    advice = [a for a in assistant.selection_advice(career, misplaced)
              if a.kind == "out_of_position"]
    assert len(advice) == 1 and others[0].display_name in advice[0].text
    action = advice[0].action
    assert action is not None and action["slot"] == striker_slot
    fixed = api.swap_in_selection(career, misplaced, action["slot"], action["player_id"])
    assert not [i for i in api.validate_selection(career, fixed) if i.severity == "error"]
    assert world.player(action["player_id"]).positions[Position.ST] >= NATURAL_THRESHOLD
    assert not [a for a in assistant.selection_advice(career, fixed)
                if a.kind == "out_of_position"]
    assert keeper in fixed.players


def _boosted(world: Dataset, pid: str, value: int = 19) -> Dataset:
    player = world.players[pid]
    attributes = type(player.attributes)(**{n: value if n not in HIDDEN_ATTRIBUTES else v
                                           for n, v in player.attributes.as_dict().items()})
    players = dict(world.players)
    players[pid] = dataclasses.replace(player, attributes=attributes)
    return dataclasses.replace(world, players=players)



def test_a_clearly_better_option_on_the_bench(world: Dataset) -> None:
    career = _career(world)
    selection = api.propose_selection(career)
    # the assistant's own XI has nothing to improve
    assert not [a for a in assistant.selection_advice(career, selection)
                if a.kind == "better_option"]
    # a reserve centre-back made far better (the XI kept as it was) is worth a swap
    reserve = next(p for p in sorted(world.squad("alvorada"), key=lambda p: p.id)
                   if p.id not in selection.players
                   and p.positions[Position.DC] >= NATURAL_THRESHOLD)
    stronger = _career(_boosted(world, reserve.id))
    advice = [a for a in assistant.selection_advice(stronger, selection)
              if a.kind == "better_option"]
    assert advice and reserve.display_name in advice[0].text
    action = advice[0].action
    assert action is not None and action["player_id"] == reserve.id
    applied = api.swap_in_selection(stronger, selection, action["slot"], action["player_id"])
    assert not [i for i in api.validate_selection(stronger, applied) if i.severity == "error"]
    assert not [a for a in assistant.selection_advice(stronger, applied)
                if a.kind == "better_option" and reserve.display_name in a.text]


# ---- US3: the tactic -------------------------------------------------------------------------


def _underdog_away(world: Dataset) -> tuple[Career, str] | None:
    for club in sorted(world.clubs):
        career = _career(world, club)
        match = assistant.next_user_match(career)
        assert match is not None
        if match.away_id != club:
            continue
        report = assistant.opposition_report(career, match.id)
        if report.band == "underdog":
            return career, match.id
    return None


def test_a_big_underdog_away_gets_the_ais_adaptation(world: Dataset) -> None:
    found = _underdog_away(world)
    assert found is not None, "the sample has an underdog away in round one"
    career, match_id = found
    tactic = api.current_tactic(career)
    advice = [a for a in assistant.tactic_advice(career, tactic, match_id) if a.kind == "adapt"]
    assert len(advice) == 1 and advice[0].action is not None
    adapted = advice[0].action["tactic"]
    options = api.tactic_options().mentality.settings
    assert options.index(adapted.mentality) <= options.index(tactic.mentality)
    assert adapted.setting("line_of_engagement") != "high_press"
    assert api.validate_tactic(career, adapted) == []


def test_an_even_match_gets_no_adaptation(world: Dataset) -> None:
    career = _career(world)
    match = assistant.next_user_match(career)
    assert match is not None
    tactic = api.current_tactic(career)
    own, theirs = 100.0, 100.0
    assert ai.pre_match(tactic, own, theirs, home=True) == tactic
    assert ai.pre_match(tactic, own, theirs, home=False) == tactic


def test_role_suggestions_are_better_suited_and_valid(world: Dataset) -> None:
    career = _career(world)
    match = assistant.next_user_match(career)
    assert match is not None
    tactic = api.current_tactic(career)
    roles = [a for a in assistant.tactic_advice(career, tactic, match.id) if a.kind == "role"]
    assert len(roles) <= assistant.params()["max_roles"]
    selection = api.propose_selection(career)
    starters = dict(selection.starters)
    for advice in roles:
        action = advice.action
        assert action is not None
        changed = api.set_role(tactic, action["slot"], action["phase"], action["role_id"])
        assert api.validate_tactic(career, changed) == []
        pid = starters[action["slot"]]
        slot = next(s for s in tactic.slots if s.slot == action["slot"])
        gain = (api.role_suitability(career, pid, action["role_id"])
                - api.role_suitability(career, pid, slot.ip_role))
        assert gain >= assistant.params()["role_gain"]


# ---- US4: the squad --------------------------------------------------------------------------


def _without(world: Dataset, club: str, keep: int, position: Position) -> Dataset:
    naturals = sorted(p.id for p in world.squad(club)
                      if p.positions[position] >= NATURAL_THRESHOLD)
    gone = set(naturals[keep:])
    memberships = {pid: m for pid, m in world.memberships.items() if pid not in gone}
    return dataclasses.replace(world, memberships=memberships)


def test_a_line_without_cover(world: Dataset) -> None:
    thin = _without(world, "alvorada", 1, Position.GK)
    advice = [a for a in assistant.squad_advice(_career(thin)) if a.kind == "cover"]
    assert any("goleiro" in a.text for a in advice)
    assert not [a for a in assistant.squad_advice(_career(world))
                if a.kind == "cover" and "goleiro" in a.text]


def _aged(world: Dataset, pid: str, age: int, on: date) -> Dataset:
    player = world.players[pid]
    born = on - timedelta(days=age * 365 + age // 4 + 30)
    players = dict(world.players)
    players[pid] = dataclasses.replace(player, date_of_birth=born)
    return dataclasses.replace(world, players=players)


def test_an_ageing_regular_and_a_youngster_ready(world: Dataset) -> None:
    career = _career(world)
    selection = api.propose_selection(career)
    regular = selection.starters[5][1]
    older = _aged(world, regular, 34, career.current_date)
    advice = assistant.squad_advice(_career(older))
    assert any(a.kind == "ageing" and older.player(regular).display_name in a.text
               for a in advice)
    # a reserve made strong and 19 years old, kept out of the XI, is ready
    reserves = sorted((p for p in world.squad("alvorada") if p.id not in selection.players
                       and p.positions[Position.MC] >= NATURAL_THRESHOLD), key=lambda p: p.id)
    young = _aged(_boosted(world, reserves[0].id, 17), reserves[0].id, 19, career.current_date)
    with_young = _career(young)
    with_young.selection = selection  # the owner's XI, without him
    youth = [a for a in assistant.squad_advice(with_young) if a.kind == "youth_ready"]
    assert any(young.player(reserves[0].id).display_name in a.text and "19 anos" in a.text
               for a in youth)


def test_the_briefing_is_deterministic(world: Dataset) -> None:
    one = assistant.briefing(_career(world), api.current_tactic(_career(world)))
    two = assistant.briefing(_career(world), api.current_tactic(_career(world)))
    assert one == two and one.report is not None


# ---- delivery: the facade and the news (T011) ------------------------------------------------


def test_the_facade_briefing(world: Dataset) -> None:
    career = _career(world)
    briefing = api.assistant_briefing(career)
    assert briefing.report is not None and briefing.report.match_id == (
        assistant.next_user_match(career).id)  # type: ignore[union-attr]


def test_the_news_has_the_report_the_day_before_and_the_squad_once(world: Dataset,
                                                                   tmp_path: Path) -> None:
    career = _career(world)
    assert not [n for n in api.career_news(career) if n.kind == "assistant"]  # before day one
    _play_until_next_user_match(career, tmp_path, matches=2)
    news = [n for n in api.career_news(career) if n.kind == "assistant"]
    reports = [n for n in news if n.text.startswith("Relatório do adversário")]
    squads = [n for n in news if n.text.startswith("Avaliação do elenco")]
    assert len(squads) == 1
    played = [m for m in career.season.sorted_matches()
              if m.id in career.season.results and "alvorada" in (m.home_id, m.away_id)]
    days = {m.kickoff.date() - timedelta(days=1) for m in played}
    assert days <= {n.day for n in reports}
    assert all(n.day <= career.current_date for n in news)
    # deterministic, and the first report has no form (nobody had played)
    assert [n.text for n in news] == [n.text for n in api.career_news(career)
                                      if n.kind == "assistant"]
    first = min(reports, key=lambda n: n.day)
    assert "Ainda não jogaram" in first.text


def test_every_suggested_action_is_valid(world: Dataset, tmp_path: Path) -> None:
    """SC-002: over the first matches of several careers, every action of the briefing applied
    alone gives a valid selection or tactic."""
    for club in sorted(world.clubs)[:4]:
        career = _career(world, club, seed=11)
        for _ in range(2):
            briefing = api.assistant_briefing(career)
            selection = api.propose_selection(career) if career.selection is None else (
                career.selection)
            tactic = api.current_tactic(career)
            for advice in briefing.selection + briefing.tactic + briefing.squad:
                action = advice.action
                if action is None:
                    continue
                if action["type"] == "swap":
                    swapped = api.swap_in_selection(career, selection, action["slot"],
                                                    action["player_id"])
                    assert not [i for i in api.validate_selection(career, swapped)
                                if i.severity == "error"], (club, advice.text)
                elif action["type"] == "role":
                    changed = api.set_role(tactic, action["slot"], action["phase"],
                                           action["role_id"])
                    assert api.validate_tactic(career, changed) == [], (club, advice.text)
                else:
                    assert api.validate_tactic(career, action["tactic"]) == [], (club,
                                                                                   advice.text)
            _play_until_next_user_match(career, tmp_path / club)
