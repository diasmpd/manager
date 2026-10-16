"""`build` from a fictional cache (spec 011 T014): pages shaped like ogol's, invented clubs and
players, never the network or private data. The dataset validates, the build is byte-stable,
and a career on it plays its first match."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from manager_core import api
from manager_core.domain.dataset import FlagKind
from manager_core.realdata.build import build
from manager_core.realdata.fetch import Fetcher
from manager_core.realdata.sources import ogol

SEASON_ID = 155
CLUBS = 12
# (squad section, player page label) for each of a club's 20 players
SHAPE = ([("Goleiro", "Goleiro")] * 2 + [("Defensor", "Zagueiro")] * 3
         + [("Defensor", "Lateral Esquerdo"), ("Defensor", "Lateral Direito Zagueiro")] * 2
         + [("Meia", "Volante"), ("Meia", "Meia Central"), ("Meia", "Meia Ofensivo")] * 2
         + [("Atacante", "Ponta Esquerda"), ("Atacante", "Ponta Direita Ponta Esquerda")]
         + [("Atacante", "Centroavante")] * 3)
MOVER = 900_001  # listed at club 0 (left) and club 1 (still there)
VETERAN = 900_002  # aged 50: outside the game's ages
NO_PAGE = 900_003  # no player page in the cache


def _staff(ogol_id: int, number: int, name: str, age: int, active: bool = True) -> str:
    state = "" if active else " inactive"
    return (f'<div class="staff{state}"><div class="number">{number}</div><div class="name">'
            f'<a title="Brasil" href="/pais/brasil"><span></span></a>'
            f'<a href="/jogador/{name.lower().replace(" ", "-")}/{ogol_id}?epoca_id={SEASON_ID}">'
            f'{name}</a></div><span>{age} anos - {100 + ogol_id % 7 * 50} mil &euro;</span></div>')


def _club_page(index: int, sections: dict[str, list[str]]) -> str:
    squad = "".join(f'<div class="section">{title}</div><div class="staff_line">'
                    f'{"".join(rows)}</div>' for title, rows in sections.items())
    return (
        '<html><head><meta charset="UTF-8"><style>:root{ --entity-color-main : #1a2b3c; '
        f'--entity-color-complementary : #fff; }}</style></head><body>'
        f'<div id="team_squad">{squad}</div><div class="section">Treinador</div>'
        '<div class="card-data__row"><span class="card-data__label">Nome</span>'
        f'<span class="card-data__value">Clube Inventado {index} FC</span></div>'
        '<div class="card-data__row"><span class="card-data__label">Ano de Fundação</span>'
        f'<span class="card-data__value">19{10 + index}-05-01</span></div>'
        '<div class="card-data__row"><span class="card-data__label">Cidade</span>'
        f'<span class="card-data__value">Cidade {index} (MG)</span></div>'
        '<div id="stadium"><div class="name"><span><a href="/estadio.php?id=1">'
        f'Estádio Inventado {index}</a></span></div>'
        f'<div class="information">Lotação<span>{5000 + 1000 * index}</span></div></div>'
        '</body></html>')


def _player_page(ogol_id: int, label: str, club_path: str, games: int, born: str) -> str:
    def row(key: str, value: str) -> str:
        return (f'<div class="card-data__row"><span class="card-data__label">{key}</span>'
                f'<span class="card-data__value">{value}</span></div>')
    return (
        '<html><head><meta charset="UTF-8"></head><body>'
        + row("Nome", f"Jogador Inventado {ogol_id}") + row("Data de Nascimento", born)
        + row("Nacionalidade", "Brasil Itália" if ogol_id % 5 == 0 else "Brasil")
        + row("Posição", label) + row("Pé preferencial", "Canhoto" if "Esquerd" in label
                                      else "Destro")
        + row("Altura / Peso", f"{176 + ogol_id % 12} cm / {72 + ogol_id % 9} kg")
        + '<table class="career"><tbody><tr><td></td><td>2026</td><td><a href="'
        f'{club_path}?epoca_id={SEASON_ID}">Clube</a></td><td>{games}</td><td>{games // 6}</td>'
        '<td>-</td></tr></tbody></table></body></html>')


def _store(cache: Path, url: str, page: str) -> None:
    path = Fetcher(cache).cache_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(page.encode("utf-8"), mtime=0))


@pytest.fixture(scope="module")
def data_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("manager-data")
    cache = repo / "cache" / "ogol"
    inputs = ["season = 2026", f"ogol_season = {SEASON_ID}", ""]
    for c in range(CLUBS):
        division = "ABCD"[c % 4] if c < 8 else "none"
        path = f"/equipe/clube-inventado-{c}/{80_000 + c}"
        inputs += ["[[clubs]]", f'club_id = "inventado-{c}"', f'short_name = "Inventado {c}"',
                   f'abbreviation = "IN{"ABCDEFGHIJKL"[c]}"', "module = 1",
                   f'division = "{division}"', 'state = "MG"', f'ogol = "{path}"', ""]
        sections: dict[str, list[str]] = {}
        for i, (section, label) in enumerate(SHAPE):
            ogol_id = 800_000 + c * 100 + i
            sections.setdefault(section, []).append(_staff(ogol_id, i + 1, f"Inventado {ogol_id}",
                                                           24 + i % 9))
            _store(cache, f"{ogol.BASE}/jogador/inventado-{ogol_id}/{ogol_id}"
                   f"?epoca_id={SEASON_ID}",
                   _player_page(ogol_id, label, path, 2 + (i * 7) % 15,
                                f"{1994 + i % 9}-03-{10 + c:02d}"))
        if c == 0:
            sections["Atacante"].append(_staff(MOVER, 77, "Inventado Viajante", 27, active=False))
            sections["Atacante"].append(_staff(VETERAN, 88, "Inventado Veterano", 50))
            sections["Meia"].append(_staff(NO_PAGE, 66, "Inventado Sem Pagina", 22))
            _store(cache, f"{ogol.BASE}/jogador/inventado-veterano/{VETERAN}"
                   f"?epoca_id={SEASON_ID}",
                   _player_page(VETERAN, "Centroavante", path, 1, "1976-01-01"))
        if c == 1:
            sections["Atacante"].append(_staff(MOVER, 17, "Inventado Viajante", 27))
            _store(cache, f"{ogol.BASE}/jogador/inventado-viajante/{MOVER}?epoca_id={SEASON_ID}",
                   _player_page(MOVER, "Centroavante", path, 9, "1999-01-20"))
        _store(cache, f"{ogol.BASE}{path}?epoca_id={SEASON_ID}", _club_page(c, sections))
    (repo / "inputs").mkdir()
    (repo / "inputs" / "mineiro.toml").write_text("\n".join(inputs), "utf-8")
    (cache / "log.csv").write_text(
        "url;fetched_at;status;bytes\nx;2026-10-08T00:00:00+00:00;200;1\n", "utf-8")
    return repo


def test_the_build_validates_and_follows_the_rules(data_repo: Path) -> None:
    out = data_repo / "datasets" / "test"
    result = build(data_repo, out)
    assert result.errors == ()
    dataset = api.load_dataset(out).dataset
    assert dataset is not None and not dataset.fictional
    assert len(dataset.clubs) == CLUBS
    club = dataset.clubs["inventado-0"]
    assert club.stadium_name == "Estádio Inventado 0" and club.stadium_capacity == 5000
    assert club.founded_year == 1910 and club.city == "Cidade 0" and club.abbreviation == "INA"
    # a player still at one club plays there, not where he was listed before
    assert dataset.memberships[f"p-og{MOVER}"].club_id == "inventado-1"
    assert f"p-og{VETERAN}" not in dataset.players
    flags = {(f.record_id, f.flag) for f in dataset.record_flags}
    assert (f"p-og{NO_PAGE}", FlagKind.INCOMPLETE) in flags
    assert all((pid, FlagKind.SYNTHESIS_CONFIDENCE) in flags for pid in dataset.players)
    assert dataset.players["p-og800000"].nationalities == ("BRA", "ITA")
    report = (out / "import-report.md").read_text("utf-8")
    assert "left out: p-og900002" in report and f"p-og{MOVER} -> inventado-1" in report
    # reputation follows the national division: A, then D, then a state-league-only club
    reputation = [dataset.clubs[f"inventado-{c}"].reputation for c in (0, 3, 8)]
    assert reputation == sorted(reputation, reverse=True) and len(set(reputation)) == 3


def test_the_build_is_byte_stable(data_repo: Path) -> None:
    first, second = data_repo / "datasets" / "a", data_repo / "datasets" / "b"
    build(data_repo, first)
    build(data_repo, second)
    for path in sorted(first.iterdir()):
        assert path.read_bytes() == (second / path.name).read_bytes(), path.name


def test_a_career_on_the_real_data_format_plays(data_repo: Path, tmp_path: Path) -> None:
    out = data_repo / "datasets" / "career"
    build(data_repo, out)
    dataset = api.load_dataset(out).dataset
    assert dataset is not None
    career = api.new_career(dataset, "real", "inventado-0", master_seed=3)
    stop = api.continue_career(career, tmp_path)
    while stop.kind != "user_match":
        stop = api.continue_career(career, tmp_path)
    api.continue_career(career, tmp_path)
    assert stop.match_id in career.season.results
