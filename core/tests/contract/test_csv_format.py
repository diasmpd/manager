"""Contract: dataset CSV format v1.0 (specs/001-core-domain-model/contracts/csv-format.md)."""

from manager_core.domain.attributes import ALL_ATTRIBUTES
from manager_core.io.schema import FILES, FORMAT_VERSION, SUPPORTED_MAJOR

EXPECTED_COLUMNS = {
    "dataset.csv": [
        "format_version", "reference_date", "fictional", "tool", "tool_version", "seed", "notes",
    ],
    "sources.csv": ["name", "url", "retrieved_on", "licence_notes"],
    "clubs.csv": [
        "club_id", "name", "short_name", "abbreviation", "city", "state", "country",
        "color_primary", "color_secondary", "stadium_name", "stadium_capacity", "founded_year",
        "reputation",
    ],
    "players.csv": [
        "player_id", "full_name", "display_name", "date_of_birth", "nationalities", "height_cm",
        "weight_kg", "left_foot", "right_foot", "potential_ability",
    ],
    "attributes.csv": ["player_id", *ALL_ATTRIBUTES],
    "positions.csv": [
        "player_id", "GK", "DL", "DC", "DR", "WBL", "WBR", "DM", "ML", "MC", "MR", "AML", "AMC",
        "AMR", "ST",
    ],
    "squads.csv": [
        "player_id", "club_id", "shirt_number", "market_value", "wage_monthly", "currency",
        "contract_expiry",
    ],
    "external_refs.csv": ["record_type", "record_id", "source", "source_id"],
    "record_flags.csv": ["record_type", "record_id", "flag", "detail"],
}

REQUIRED_FILES = {
    "dataset.csv", "sources.csv", "clubs.csv", "players.csv", "attributes.csv", "positions.csv",
}


def test_version() -> None:
    assert FORMAT_VERSION == "1.0"
    assert SUPPORTED_MAJOR == 1


def test_files_and_column_order() -> None:
    assert {name: [c.name for c in spec.columns] for name, spec in FILES.items()} == EXPECTED_COLUMNS


def test_required_files() -> None:
    assert {name for name, spec in FILES.items() if spec.required} == REQUIRED_FILES


def test_no_integrity_file_in_v1_0() -> None:
    assert "integrity.csv" not in FILES


def test_hidden_attribute_columns_are_optional() -> None:
    spec = FILES["attributes.csv"]
    optional = {c.name for c in spec.columns if not c.required}
    assert optional == set(ALL_ATTRIBUTES[47:])
