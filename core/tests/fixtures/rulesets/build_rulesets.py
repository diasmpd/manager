"""Builds the broken ruleset fixtures (one defect per R-code) from the bundled Liga Única.

Run from `core/`: `python tests/fixtures/rulesets/build_rulesets.py`. Each fixture gets an
`<name>.expected.txt` with the expected "<code> <path>" lines.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = (HERE.parents[2] / "src/manager_core/reference/competitions/test-liga-unica.toml").read_text(
    "utf-8")

SIDE_TRACK = """
[[stages]]
id = "copa"
name = "Copa"
type = "knockout"
track = "copa"
title = "Copa de Teste"
legs = 1
entrants = [{ from = "turno-returno", rule = "overall_places", places = [2, 3] }]
pairing = "campaign_high_low"
tie_rule = "penalties"
venue = "home"
"""

# name -> (replacements, appended text, expected "<code> <path>" lines)
CASES: dict[str, tuple[list[tuple[str, str]], str, list[str]]] = {
    "R001_invalid_toml": ([("format_version = 1", "format_version = = 1")], "", ["R001"]),
    "R002_missing_name": ([('name = "Liga Única de Teste"\n', "")], "",
                          ["R002 competition.name"]),
    "R003_unknown_matching": ([('matching = "all"', 'matching = "everyone"')], "",
                              ["R003 stages[0].matching"]),
    "R004_groups_vs_participants": ([("group_count = 1", "group_count = 2")], "",
                                    ["R004 stages[0]"]),
    "R005_unknown_source": ([('{ from = "turno-returno", rule = "overall_places"',
                              '{ from = "fase-fantasma", rule = "overall_places"')], "",
                            ["R005 stages[1].entrants[0].from"]),
    "R006_place_out_of_range": ([("overall_places = [8, 8]", "overall_places = [8, 9]")], "",
                                ["R006 stages[0].outcomes[0]"]),
    "R007_odd_entrants": ([("places = [1, 2]", "places = [1, 3]")], "",
                          ["R007 stages[1].entrants"]),
    "R008_neutral_without_venue": ([('venue = "home"', 'venue = "neutral"')], "",
                                   ["R008 stages[1].venue"]),
    "R009_no_draw_last": ([('tiebreakers = ["goal_difference", "wins", "goals_for", "draw"]',
                            'tiebreakers = ["goal_difference", "draw", "wins"]')], "",
                          ["R009 scoring.tiebreakers"]),
    "R010_window_reversed": ([('window_end = "04-30"', 'window_end = "01-10"')], "",
                             ["R010 calendar.window"]),
    "R011_other_groups_one_group": ([('matching = "all"', 'matching = "other_groups"')], "",
                                    ["R011 stages[0].matching"]),
    "R012_tracks_overlap": ([], SIDE_TRACK, ["R012 stages[2].entrants[0]"]),
    "R013_valid_to_before_from": ([("valid_from = 2026", "valid_from = 2026\nvalid_to = 2025")],
                                  "", ["R013 competition.valid_to"]),
    "R014_rest_impossible": ([("min_rest_hours = 66", "min_rest_hours = 100")], "",
                             ["R014 calendar"]),
    "multi_three_defects": ([("group_count = 1", "group_count = 2"),
                             ('venue = "home"', 'venue = "neutral"'),
                             ("valid_from = 2026", "valid_from = 2026\nvalid_to = 2025")], "",
                            ["R013 competition.valid_to", "R004 stages[0]",
                             "R008 stages[1].venue"]),
}


def build() -> None:
    for name, (replacements, extra, expected) in CASES.items():
        text = BASE
        for old, new in replacements:
            assert text.count(old) == 1, (name, old)
            text = text.replace(old, new)
        (HERE / f"{name}.toml").write_text(text + extra, "utf-8")
        (HERE / f"{name}.expected.txt").write_text("\n".join(expected) + "\n", "utf-8")


if __name__ == "__main__":
    build()
