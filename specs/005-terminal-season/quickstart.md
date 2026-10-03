# Quickstart: Playable Season in the Terminal (005)

Run on Windows from the repository root, in Windows Terminal, with the `.venv` from 001
activated.

## 1. Install and check

```powershell
pip install -e "core[dev]" -e "tui[dev]"
cd core; ruff check .; mypy; pytest -q -m "not milestone"; cd ..
cd tui; ruff check .; mypy; pytest -q; cd ..
```

## 2. Play

```powershell
python -m manager_core career new minha --club alvorada   # once
python -m manager_tui minha
```

| Key | Action |
|---|---|
| Space | Continuar |
| H / E / T / C / N | Home / Squad / Tables / Calendar / News |
| [ and ] | Previous or next month (calendar) |
| Enter (squad) | Player profile (Esc closes) |
| Q | Save and quit |

**Team selection**, which opens before each of your matches:

| Key | Action |
|---|---|
| Tab | Switch between the XI and the other players |
| Enter | Swap the highlighted XI slot with the highlighted player |
| F | Next formation |
| A | Assistant pick |
| C | Confirm |
| Esc | Back |

**Match day:**

| Key | Action |
|---|---|
| 1 / 2 / 3 | Slow / normal / fast feed |
| 4 or Space | Skip to the end (stats) |
| Enter | Continue |

Expected:
- the home screen shows the date, the next match, the position and the news;
- Continuar stops before each of your matches with team selection;
- suspended players are marked and cannot be picked;
- the feed lists goals, cards and substitutions with the score, then the stats;
- the season ends with a review, and Continuar starts the next one;
- quitting saves the career.

The minimum terminal size is 100 × 30. A smaller window shows a message.
