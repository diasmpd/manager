"""Fictional identities for the sample world. Clubs and towns are invented in the style of
Minas Gerais football. No real club names, badges or people (FR-024)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClubIdentity:
    id: str
    name: str
    short_name: str
    abbreviation: str
    city: str
    color_primary: str
    color_secondary: str
    stadium_name: str
    stadium_capacity: int
    founded_year: int
    reputation: int
    tier: str  # strong / mid / small


CLUBS: tuple[ClubIdentity, ...] = (
    # strong
    ClubIdentity("vale-do-ouro", "Sociedade Esportiva Vale do Ouro", "Vale do Ouro", "SVO",
                 "Vale do Ouro", "#0B3D91", "#F2C200", "Estádio Ourão", 42000, 1912, 15, "strong"),
    ClubIdentity("serra-negra", "Esporte Clube Serra Negra", "Serra Negra", "ECS",
                 "Serra Negra de Minas", "#111111", "#FFFFFF", "Arena da Serra", 38000, 1921, 14,
                 "strong"),
    ClubIdentity("alvorada", "Grêmio Recreativo Alvorada", "Alvorada", "GRA", "Alvorada",
                 "#C8102E", "#FFFFFF", "Estádio do Alvorecer", 31000, 1908, 13, "strong"),
    # mid
    ClubIdentity("mineracao", "Mineração Futebol Clube", "Mineração", "MFC", "Itaverde",
                 "#1B5E20", "#FFFFFF", "Estádio da Mina", 18000, 1935, 11, "mid"),
    ClubIdentity("ferroviario", "Ferroviário Esporte Clube Mantiqueira", "Ferroviário", "FEM",
                 "Mantiqueira", "#8B0000", "#F5F5F5", "Estádio da Estação", 15000, 1929, 10, "mid"),
    ClubIdentity("rio-turvo", "Associação Desportiva Rio Turvo", "Rio Turvo", "ART", "Rio Turvo",
                 "#0057B8", "#FFD100", "Estádio Beira-Rio Turvo", 13000, 1940, 10, "mid"),
    ClubIdentity("pedra-branca", "Esporte Clube Pedra Branca", "Pedra Branca", "EPB",
                 "Pedra Branca", "#F4F4F4", "#2E7D32", "Estádio do Pedregal", 12000, 1947, 10,
                 "mid"),
    ClubIdentity("uniao-operaria", "União Operária de Cristalina", "União Operária", "UOC",
                 "Cristalina de Minas", "#F57C00", "#111111", "Estádio Operário", 14000, 1933, 9,
                 "mid"),
    # small
    ClubIdentity("jequitiba", "Jequitibá Esporte Clube", "Jequitibá", "JEC", "Jequitibá do Norte",
                 "#6A1B9A", "#FFFFFF", "Estádio do Cerrado", 8000, 1951, 8, "small"),
    ClubIdentity("sete-lagos", "Sete Lagos Futebol Clube", "Sete Lagos", "SLF", "Sete Lagos",
                 "#00838F", "#FFFFFF", "Estádio das Lagoas", 9000, 1962, 7, "small"),
    ClubIdentity("campo-florido", "Clube Esportivo Campo Florido", "Campo Florido", "CEF",
                 "Campo Florido", "#FBC02D", "#1B5E20", "Estádio das Flores", 6000, 1958, 7,
                 "small"),
    ClubIdentity("sertanejo", "Sertanejo Esporte Clube", "Sertanejo", "SEC", "Bom Sertão",
                 "#795548", "#FFFFFF", "Estádio do Sertão", 5000, 1966, 6, "small"),
)

FIRST_NAMES: tuple[str, ...] = (
    "João", "Pedro", "Lucas", "Gabriel", "Rafael", "Bruno", "Thiago", "Diego", "Caio", "Felipe",
    "Matheus", "Vinícius", "André", "Igor", "Renan", "Wesley", "Everton", "Danilo", "Hugo", "Léo",
    "Marcos", "Rodrigo", "Gustavo", "Alex", "Fábio", "Murilo", "Kaio", "Douglas", "Otávio",
    "Emerson", "Luan", "Arthur", "Davi", "Henrique", "Samuel", "Nathan", "Eduardo", "Ramon",
    "Wallace", "Jefferson", "Anderson", "Patrick", "Yago", "Ítalo", "Wellington", "Raul", "Jonas",
)

SURNAMES: tuple[str, ...] = (
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Rodrigues", "Almeida",
    "Nunes", "Carvalho", "Gomes", "Ribeiro", "Martins", "Rocha", "Barbosa", "Teixeira", "Moura",
    "Cardoso", "Freitas", "Araújo", "Mendes", "Batista", "Ramos", "Vieira", "Monteiro", "Pinto",
    "Correia", "Dias", "Farias", "Fonseca", "Campos", "Machado", "Borges", "Lopes", "Andrade",
    "Moreira", "Nascimento", "Queiroz", "Siqueira",
)

NICKNAMES: tuple[str, ...] = (
    "Juninho", "Netinho", "Pelezinho", "Tiquinho", "Biel", "Dudu", "Cacá", "Toninho", "Zé Rafael",
    "Gui", "Pedrinho", "Didi", "Nenê", "Fumaça", "Bolinha", "Careca", "Baiano", "Mineiro",
    "Paulista", "Gaúcho", "Tchê", "Neguinho", "Lelê", "Kiko", "Tico",
)

FOREIGN_NATIONS: tuple[str, ...] = ("ARG", "URU", "PAR", "COL", "VEN", "ECU", "BOL")
SECOND_NATIONALITIES: tuple[str, ...] = ("ITA", "POR", "ESP")
