# Contract: CLI additions (008)

All output in pt-BR. Exit codes as in 003.

| Command | Output |
|---|---|
| `calibrate --engine positional [--gate pr\|milestone] [--baseline PATH] [--write PATH]` | The same table as the quick sim's `calibrate`, for the league sample's targets played by the positional engine (PR 300 matches, milestone 1,500). At the PR gate only the robust metrics (goals per match; the home, draw and away shares; cards) can be FORA, and the other primary targets show AVISO. At the milestone gate every primary target gates, and a second table shows the cross-validation: each metric on the positional engine and on the quick sim over the same fixtures, the tolerance, and OK or FORA. It exits 1 if a gating target or a cross-validation row is out. No caution or exploit line. |
| `calibrate --engine quick` | The default: the quick sim's gate, unchanged. |

The JSON report (`--write`) has `"engine"` (`quick` or `positional`) and, for the positional
milestone gate, `"cross_validation"`: `matches`, `passed`, and per metric `positional`, `quick`,
`tolerance` and `ok`.
