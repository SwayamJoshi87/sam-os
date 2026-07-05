#!/usr/bin/env python3
"""Sunday 8pm — weekly review of living schedule."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.schedule import stats as week_stats
from samos.schedule import week_history

hist = week_history(7)
stats_rows = week_stats(7)

print("📊 weekly review — last 7 days\n")
if not stats_rows:
    print("no data yet")
else:
    print("by category:")
    for r in stats_rows:
        done = r["done"] or 0
        skp = r["skipped"] or 0
        mov = r["moved"] or 0
        tot = r["total"]
        if not tot:
            continue
        pct = done / tot * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(
            f"  {r['category']:<12} {bar} {done}/{tot} ({pct:.0f}%)  {skp} skipped  {mov} moved"
        )

skips = [r for r in hist if r["status"] == "skipped" and r["reason"]]
reasons = Counter(r["reason"] for r in skips)
if reasons:
    print("\ntop skip reasons:")
    for reason, count in reasons.most_common(5):
        print(f"  • {reason} ({count})")

moves = [r for r in hist if r["status"] == "moved"]
if moves:
    print(f"\ntotal moves: {len(moves)}")
    by_task = Counter(r["name"] for r in moves)
    for name, count in by_task.most_common(3):
        print(f"  • {name}: {count} move(s)")
