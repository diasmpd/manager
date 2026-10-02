"""Plays one match between two generated teams and prints the commentary.

Usage: python run_match.py [seed]
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from manager import Match, make_team

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
home = make_team("Leões do Cerrado", quality=12, seed=1)
away = make_team("Tubarões FC", quality=11, seed=2)

match = Match(home, away, seed=seed)
for event in match.simulate():
    if event.kind in ("foul",):
        continue  # too noisy for the console
    print(f"{event.minute:>5}'  {event.text}")
