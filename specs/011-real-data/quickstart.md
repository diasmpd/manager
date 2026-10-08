# Quickstart: Real Data for Minas Gerais Clubs

**Prerequisites**:
- the private repository cloned beside the code, at `..\manager-data`;
- `inputs/mineiro.toml` filled, with ids per source and colours where needed.

1. **Collect, once and gently** (about 30 minutes for Módulo I, paced):

   `python -m manager_core.realdata collect --source ogol --competition mineiro-1 --data-repo
   ..\manager-data`, then the same with `--source wikipedia`.

   Expected: about 12 club pages and about 350 player pages in `cache/`, and nothing refused by
   robots. A second run fetches nothing.
2. **Build**:

   `… build --competition mineiro-1 --out datasets/mineiro-2026 --data-repo ..\manager-data`.

   Expected:
   - the dataset validates;
   - every Módulo I club has 22 or more players (SC-002);
   - the report shows Spearman 0.7 or more against the 2026 table (SC-003).
3. **Play**: start a career with the dataset, pick Pouso Alegre, and play a match day. The look
   uses Pouso Alegre's real colours.
4. **Correct**: `… correct --record player:p-og<id> --field finishing --value 15`. Rebuild, and
   the value stays (SC-004). The report lists the correction.
5. **Excel**: open `players.csv` in pt-BR Excel, change a name, save it, and load the dataset. It
   loads with that one change (SC-007).
6. **Guard**: `… check-public --repo .` passes, and the test suite includes it (SC-006).
