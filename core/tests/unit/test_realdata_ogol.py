"""ogol page parsers (spec 011 T010), on fictional fixtures that mirror the real pages."""

from pathlib import Path

from manager_core.realdata.sources.ogol import parse_club, parse_player

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "realdata"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text("utf-8")


def test_club_identity_colours_and_squad() -> None:
    club = parse_club(_read("ogol_club.html"))
    assert club.name == "Clube Fictício Futebol Clube"
    assert club.founded == "1920"  # only the year is known
    assert club.city == "Vila Imaginária" and club.state == "MG"
    assert club.colors == ("#1A2B3C", "#FFFFFF")
    active = [p for p in club.squad if p.active]
    assert [p.ogol_id for p in club.squad] == [700001, 700002, 700003, 700004, 700005]
    assert [p.ogol_id for p in active] == [700001, 700003, 700004, 700005]  # inactive: left
    keeper, _gone, back, mid, forward = club.squad
    assert keeper.group == "GK" and keeper.number == 1 and keeper.age == 31
    assert keeper.nationality == "Brasil" and keeper.name == "João Goleiro"
    assert back.group == "D" and back.number is None and back.nationality == "Paraguai"
    assert back.market_value_eur == 150_000
    assert mid.group == "M" and mid.name == "Meia São João" and mid.market_value_eur is None
    assert forward.group == "A" and forward.market_value_eur == 1_500_000


def test_player_facts_and_career() -> None:
    player = parse_player(_read("ogol_player.html"), 700003)
    assert player.full_name == "Zagueiro Paraguaio Inventado"
    assert player.birth_date == "1998-02-10"
    assert player.nationality == "Paraguai"
    assert player.position == "Defesa Central"
    assert player.foot == "left"
    assert player.height_cm == 188 and player.weight_kg == 84
    # the blank season cell continues the season above; "-" is none
    assert [(s.season, s.team_id, s.games, s.goals, s.assists) for s in player.career] == [
        ("2026", 90001, 14, 1, 0), ("2025", 90002, 30, 3, 2), ("2025", 90001, 5, 0, 0)]
