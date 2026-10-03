# Contract: CLI `career` commands (004)

Output is in pt-BR. Exit codes: 0 ok; 1 invalid (corrupt save, refused version); 2 usage;
3 not found (save, club).

**Shared options**: `--saves DIR` (default `saves/`). The global `--data` (001) is the starting
world for `career new`.

| Command | Output |
|---|---|
| `career new NAME --club ID [--seed N]` | Creates and saves the career. Prints the club, the season year, the group draw and the first match. The default seed is derived from the name. |
| `career list` | Saves with name, club, date, season and saved-at (most recent first) |
| `career status NAME` | Date, next user match (date, opponent, venue), user club's table position, suspended players of the user club, the last stop |
| `career continue NAME [--to-season-end]` | Plays to the next stop and prints it: the user match day ahead, the day's events, or the season review. Saves the career, and autosaves weekly. `--to-season-end` keeps continuing until the season-end stop. |
| `career save NAME --as NEW` | Copies the career to a new named save |
| `career delete NAME` | Deletes a named save; `autosave` cannot be deleted this way |
| `career history NAME` | One line per finished season: year, champion, user club's position, relegated, promoted |

`season … --career NAME` runs every 002 and 003 view (`groups`, `fixtures`, `table`, `bracket`,
`day`, `calendar`, `outcomes`, `match`, `scorers`) on the career's current season, up to its
current date.
