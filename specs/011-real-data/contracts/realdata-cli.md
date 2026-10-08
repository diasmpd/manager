# Contract: the real-data CLI

`python -m manager_core.realdata <command> --data-repo <path to manager-data> [options]`

Every command refuses a `--data-repo` inside the public repository (R7). Exit codes:
- 0: success;
- 1: a validation error or a refused write;
- 2: a source stopped (403 or 429, or robots).

| Command | Options | Effect |
|---|---|---|
| `collect` | `--source ogol\|wikipedia` `--competition mineiro-1\|mineiro-2` `[--refresh]` `[--delay 4.0]` | Fetches the club pages and then each player page for the clubs in `inputs/mineiro.toml`, through the paced, robots-aware, cached fetcher. Prints progress, from cache or fetched. Network only for pages missing from the cache, or every page with `--refresh`. |
| `build` | `--competition …` `--out datasets/<name>` | Parse, merge, synthesise, apply corrections, then write the 001 dataset and `import-report.md`. Offline: it reads only the cache. Deterministic. |
| `report` | `--out datasets/<name>` | Prints the import report, including the SC-003 ranking against the real table. |
| `correct` | `--record player:p-og123 --field finishing --value 14 [--note …]` | Appends a row to `corrections.csv` with the current value as `old_value` and today's date. |
| `check-public` | `--repo <public repo>` | The R7 guard, as a command. Also run by the test suite. |

The dataset loads like the sample: `python -m manager_core --data <manager-data>/datasets/<name>
…`, or the client's `core.cfg` data path.
