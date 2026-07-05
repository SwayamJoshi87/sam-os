#!/usr/bin/env python3
"""Log workouts — CLI wrapper around samos.gym."""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos import gym


def show_today():
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    rows = gym.recent_workouts(0)
    today_rows = [r for r in rows if r["date"] == today]
    if not today_rows:
        print("no workout logged today")
        return
    cur_gym = None
    for r in today_rows:
        if r["gym"] != cur_gym:
            cur_gym = r["gym"]
            print(f"\n🏋️ {cur_gym}:")
        print(f"   {r['exercise']}: {r['weight']}lb × {r['reps']} × {r['sets']}")


def show_summary(days: int = 7):
    from datetime import datetime

    since = (datetime.now() - __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
    rows = [r for r in gym.recent_workouts(days) if r["date"] >= since]
    if not rows:
        print(f"no workouts in last {days} days")
        return
    cur_date = None
    for r in rows:
        if r["date"] != cur_date:
            cur_date = r["date"]
            print(f"\n📅 {cur_date} — {r['gym']}")
        print(f"   {r['exercise']}: {r['weight']}lb × {r['reps']} × {r['sets']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_today()
    elif sys.argv[1] == "today":
        show_today()
    elif sys.argv[1] == "summary":
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
        show_summary(days)
    elif sys.argv[1] == "log" and len(sys.argv) >= 3:
        gym_name = sys.argv[2]
        raw = " ".join(sys.argv[3:])
        entries = gym.parse_workout(raw)
        if not entries:
            print(f"could not parse: {raw}")
            print("format: log <gym> <exercise> <weight>x<reps>[x<sets>] ...")
            print("e.g.: log office bench 135x10x3 squat 185x5x3")
            sys.exit(1)
        result = gym.log_workout(gym_name, entries)
        print(f"✅ logged {result['logged_count']} exercises to {gym_name}")
        if result["new_prs"]:
            print(f"🏆 {len(result['new_prs'])} new PR(s)!")
            for pr in result["new_prs"]:
                print(
                    f"   {pr['exercise']} ({pr['gym']}): {pr['weight']}lb × {pr['reps']} "
                    f"→ est 1RM {pr['estimated_1rm']}lb"
                )
    elif sys.argv[1] == "prs":
        gym_name = sys.argv[2] if len(sys.argv) >= 3 else None
        rows = gym.list_prs(gym_name)
        if not rows:
            print("no PRs yet — go lift")
        else:
            for r in rows:
                print(
                    f"  {r['exercise']} ({r['gym']}): {r['weight']}lb × {r['reps']} "
                    f"→ est 1RM {r['estimated_1rm']}lb ({r['achieved_at']})"
                )
    elif sys.argv[1] == "help":
        print(
            """workout.py [command]
  today              — show today's workout
  summary [N]        — last N days summary
  log <gym> <data>   — log workout
                       format: exercise weightxreps[xsets]
                       e.g.: log office bench 135x10x3 squat 185x5x3
                       use BW or bw for bodyweight exercises
                       e.g.: log home pullup bw x 8 x 3"""
        )
    else:
        print(f"unknown: {' '.join(sys.argv[1:])}")
