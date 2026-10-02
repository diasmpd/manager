# Contract: Competition Ruleset Format v1 (TOML)

A ruleset describes one competition's format as data (FR-001). The files live in
`core/src/manager_core/reference/competitions/<id>.toml`. Comments (`#`) should cite the
regulation article each rule comes from.

## Mineiro 2026 (abridged reference example)

```toml
format_version = 1

[competition]
id = "mg-modulo-i-2026"
name = "Campeonato Mineiro – Módulo I"
short_name = "Mineiro"
state = "MG"
country = "BRA"
participants = 12

[scoring]
win = 3
draw = 1
loss = 0
# Customary Brazilian order; to be confirmed against the FMF 2026 regulation.
tiebreakers = ["wins", "goal_difference", "goals_for", "head_to_head",
               "fewer_red_cards", "fewer_yellow_cards", "draw"]

[calendar]
window_start = "01-08"      # month-day; the first full weekend on or after this date opens the window
window_end = "03-08"
weekend_days = ["sat", "sun"]
midweek_days = ["wed", "thu"]
kickoff_weekend = "16:00"
kickoff_midweek = "21:30"
min_rest_hours = 66
avoid_windows = ["fifa"]

[venues.neutral]
name = "Arena Estadual das Gerais"   # fictional Mineirão equivalent
city = "Vale do Ouro"
capacity = 62000

[[stages]]
id = "primeira-fase"
type = "groups"
group_count = 3
group_size = 4
matching = "other_groups"   # each club plays the clubs of the two other groups
rounds = 1
draw = "pots_by_reputation"
outcomes = [{ kind = "relegated", overall_places = [11, 12] }]

[[stages]]
id = "semifinal"
type = "knockout"
track = "main"
legs = 2
entrants = [
  { from = "primeira-fase", rule = "group_winners" },
  { from = "primeira-fase", rule = "best_of_place", place = 2, count = 1 },
]
pairing = "campaign_1v4_2v3"
deciding_leg_host = "better_campaign"
tie_rule = "penalties"
venue = "home"

[[stages]]
id = "final"
type = "knockout"
track = "main"
title = "Campeão Mineiro"
legs = 1
entrants = [{ from = "semifinal", rule = "winners_of" }]
pairing = "campaign_high_low"
tie_rule = "penalties"
venue = "neutral"

[[stages]]
id = "inconfidencia-semifinal"
type = "knockout"
track = "inconfidencia"
legs = 2
entrants = [{ from = "primeira-fase", rule = "overall_places", places = [5, 8] }]
pairing = "campaign_1v4_2v3"
deciding_leg_host = "better_campaign"
tie_rule = "points_then_campaign"
venue = "home"
dates_with = "semifinal"

[[stages]]
id = "inconfidencia-final"
type = "knockout"
track = "inconfidencia"
title = "Troféu Inconfidência"
legs = 2
entrants = [{ from = "inconfidencia-semifinal", rule = "winners_of" }]
pairing = "campaign_high_low"
deciding_leg_host = "better_campaign"
tie_rule = "points_then_campaign"
venue = "home"
dates_with = "final"
```

## Keys

| Key | Values | Notes |
|---|---|---|
| `format_version` | `1` | A file with a higher major version is refused |
| `stages[].type` | `groups`, `knockout` | |
| `matching` | `own_group`, `other_groups`, `all` | `all` ignores groups |
| `rounds` | `1`, `2` | 2 means home and away |
| `draw` | `pots_by_reputation`, `fixed` | `fixed` reads `groups = [["id", …], …]` |
| `entrants[].rule` | `group_winners`; `best_of_place` (`place`, `count`); `overall_places` (`places = [from, to]`); `winners_of` | |
| `pairing` | `campaign_1v4_2v3`, `campaign_high_low` | Campaign means first-phase overall classification |
| `deciding_leg_host` | `better_campaign` | The better campaign hosts the second leg |
| `tie_rule` | `penalties`, `points_then_campaign` | `points_then_campaign` compares points over the legs, then the better campaign (no penalties) |
| `venue` | `home`, `neutral` | `neutral` needs `[venues.neutral]` |
| `dates_with` | stage id | Share that stage's date slots, plus the next free slot if more legs are needed |
| `tiebreakers` | ordered subset of `wins`, `goal_difference`, `goals_for`, `head_to_head`, `fewer_red_cards`, `fewer_yellow_cards`, `draw` | `draw` must be last |

## Reserved calendar windows (`reference/calendar/brazil.toml`)

```toml
[[windows]]
label = "fifa"
name = "Data FIFA"
from = "03-23"
to = "03-31"
blocks = ["state"]
```

Windows apply to every year. The ones that block state competitions constrain date generation.
The others only label the calendar.
