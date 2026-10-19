"""pt.wikipedia club infobox (spec 011 T012), on a fictional page shaped like the real ones."""

from pathlib import Path

from manager_core.realdata.sources.wikipedia import capacity, parse_club, url

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "realdata" / "wikipedia_club.html"


def test_the_infobox_identity() -> None:
    club = parse_club(FIXTURE.read_text("utf-8"))
    assert club.name == "Clube Fictício Futebol Clube"
    assert club.founded == 1920  # the first founding, not the refoundation
    assert club.city == "Vila Imaginária"
    assert club.stadium == "Fazendão"
    assert club.capacity == 12_480 and club.capacity_exact


def test_capacities_exact_and_rounded() -> None:
    assert capacity("62 mil") == (62_000, False)
    assert capacity("23.018") == (23_018, True)
    assert capacity("61\xa0846 [1]") == (61_846, True)
    assert capacity("1500") == (1_500, True)
    assert capacity("") == (None, False)


def test_a_page_without_an_infobox() -> None:
    club = parse_club("<html><body><p>nada</p></body></html>")
    assert (club.name, club.founded, club.city, club.capacity) == (None, None, None, None)


def test_urls() -> None:
    assert url("Uberlândia Esporte Clube") == (
        "https://pt.wikipedia.org/wiki/Uberl%C3%A2ndia_Esporte_Clube")


def test_identity_merge_rules() -> None:
    """R3: Wikipedia for name, city and founding; the exact capacity; ogol's own stadium (and its
    capacity) when the sources name different grounds; every real disagreement reported."""
    from manager_core.realdata.build import _identity
    from manager_core.realdata.sources.ogol import RawClub
    from manager_core.realdata.sources.wikipedia import WikiClub

    raw = RawClub("Clube Inventado", "2008-11-27", "Vila Del Rei", "MG", None, (),
                  "José Inventado (Inventadão)", 7500)
    same = WikiClub("Clube Inventado FC", 2008, "Vila del-Rei", "Inventadão", 8675, True)
    identity, notes = _identity(raw, same)
    assert identity["name"] == "Clube Inventado FC" and identity["city"] == "Vila del-Rei"
    assert identity["stadium"] == "José Inventado (Inventadão)"  # ogol's fuller name
    assert identity["capacity"] == 8675  # Wikipedia's exact figure
    assert notes == ["capacity: Wikipedia 8675, ogol 7500 (8675 used)"]
    # a rounded capacity yields to ogol's exact one, without a note when they agree
    rounded = WikiClub("Clube Inventado", 2008, "Vila", "Inventadão", 8000, False)
    identity, notes = _identity(raw, rounded)
    assert identity["capacity"] == 7500 and notes == []
    # another ground altogether: ogol's 2026 stadium with its own capacity; founding differs
    other = WikiClub("Clube Inventado", 2019, "Vila", "Estádio Outro Nome", 2000, True)
    identity, notes = _identity(raw, other)
    assert (identity["stadium"], identity["capacity"], identity["founded"]) == (
        "José Inventado (Inventadão)", 7500, 2019)
    assert len(notes) == 2 and notes[0].startswith("founded: Wikipedia 2019, ogol 2008")
    # no Wikipedia page: ogol alone, nothing to report
    assert _identity(raw, None) == ({"name": "Clube Inventado", "city": "Vila Del Rei",
                                     "founded": 2008, "stadium": "José Inventado (Inventadão)",
                                     "capacity": 7500}, [])
