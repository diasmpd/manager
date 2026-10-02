"""Simulates many matches and prints league-wide averages, to check the engine looks like real football.

Real-world reference (Brasileirão, approx.): 2.3-2.6 goals, ~25 shots, ~25 fouls, ~4.5 yellows per match,
home win ~48%, draw ~27%.

Usage: python calibrate.py [n_matches]
"""
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

from manager import Match, make_team

n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
totals = Counter()
results = Counter()
for i in range(n):
    home = make_team("A", quality=11, seed=i * 2)
    away = make_team("B", quality=11, seed=i * 2 + 1)
    m = Match(home, away, seed=i)
    m.simulate()
    for e in m.events:
        totals[e.kind] += 1
    h, a = m.score
    results["home" if h > a else "away" if a > h else "draw"] += 1

shots = totals["goal"] + totals["shot_saved"] + totals["shot_wide"]
print(f"{n} partidas")
print(f"gols/jogo:        {totals['goal'] / n:.2f}")
print(f"finalizações/jogo:{shots / n:.1f}")
print(f"faltas/jogo:      {(totals['foul'] + totals['penalty']) / n:.1f}")
print(f"amarelos/jogo:    {totals['yellow'] / n:.2f}")
print(f"expulsões/jogo:   {(totals['red'] + totals['second_yellow']) / n:.2f}")
print(f"pênaltis/jogo:    {totals['penalty'] / n:.2f}")
print(f"mandante/empate/visitante: "
      f"{results['home'] / n:.0%} / {results['draw'] / n:.0%} / {results['away'] / n:.0%}")
