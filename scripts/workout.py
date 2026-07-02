#!/usr/bin/env python3
"""Log workouts — parses 'exercise weightxrepsxsets' format."""

import sqlite3, re, sys
from datetime import datetime

DB = "/home/server/data/schedule.db"

def parse_workout(text: str) -> list[dict]:
    """Parse 'bench 135x10x3 deadlift 225x5 squat 185x8' into structured rows."""
    # match: exercise_name followed by weight x reps [x sets]
    # weight can be bodyweight/bw/0
    pattern = r'([a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+)?)\s+(\d+\.?\d*|bw|BW)\s*x\s*(\d+)(?:\s*x\s*(\d+))?'
    matches = re.findall(pattern, text.lower().strip())
    if not matches:
        # try simple format: exercise reps weight
        pattern2 = r'([a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+)?)\s+(\d+)\s+x\s+(\d+\.?\d+)(?:\s+x\s*(\d+))?'
        matches = re.findall(pattern2, text.lower().strip())
    
    results = []
    for m in matches:
        name = m[0].strip()
        weight = float(m[1]) if m[1].replace('.','').isdigit() else 0.0
        reps = int(m[2])
        sets = int(m[3]) if m[3] else 1
        results.append({"exercise": name, "weight": weight, "reps": reps, "sets": sets})
    return results


def epley_1rm(weight: float, reps: int) -> float:
    """Estimated 1-rep max via Epley formula."""
    if weight <= 0 or reps <= 0:
        return 0.0
    return round(weight * (1 + reps / 30.0), 1)


def update_prs(gym: str, entries: list[dict]):
    """For each exercise × gym, check if new entries beat the existing PR."""
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    prs = []
    for e in entries:
        if e["weight"] <= 0 or e["reps"] <= 0:
            continue
        new_1rm = epley_1rm(e["weight"], e["reps"])
        existing = conn.execute(
            "SELECT weight, reps, estimated_1rm FROM prs WHERE exercise=? AND gym=?",
            (e["exercise"], gym)
        ).fetchone()
        if existing is None:
            # no PR for this exercise × gym yet → this one's a PR
            cur = conn.execute("SELECT id FROM workouts WHERE date=? AND exercise=? AND gym=? ORDER BY id DESC LIMIT 1",
                               (today, e["exercise"], gym)).fetchone()
            wid = cur[0] if cur else None
            conn.execute("""INSERT INTO prs(exercise, gym, weight, reps, estimated_1rm, workout_id, achieved_at)
                           VALUES(?,?,?,?,?,?,?)""",
                        (e["exercise"], gym, e["weight"], e["reps"], new_1rm, wid, today))
            prs.append((e["exercise"], gym, e["weight"], e["reps"], new_1rm))
        else:
            # existing PR found — compare estimated 1RM
            if new_1rm > existing[2]:
                cur = conn.execute("SELECT id FROM workouts WHERE date=? AND exercise=? AND gym=? ORDER BY id DESC LIMIT 1",
                                   (today, e["exercise"], gym)).fetchone()
                wid = cur[0] if cur else None
                conn.execute("""UPDATE prs SET weight=?, reps=?, estimated_1rm=?, workout_id=?, achieved_at=?
                               WHERE exercise=? AND gym=?""",
                            (e["weight"], e["reps"], new_1rm, wid, today, e["exercise"], gym))
                prs.append((e["exercise"], gym, e["weight"], e["reps"], new_1rm))
    conn.commit()
    conn.close()
    return prs


def log_workout(gym: str, entries: list[dict]):
    conn = sqlite3.connect(DB)
    today = datetime.now().strftime("%Y-%m-%d")
    for e in entries:
        conn.execute(
            "INSERT INTO workouts(date, gym, exercise, weight, reps, sets) VALUES(?,?,?,?,?,?)",
            (today, gym, e["exercise"], e["weight"], e["reps"], e["sets"])
        )
    conn.commit()
    conn.close()
    return update_prs(gym, entries)


def show_today():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT gym, exercise, weight, reps, sets FROM workouts WHERE date=? ORDER BY id
    """, (today,)).fetchall()
    if not rows:
        print("no workout logged today")
        return
    cur_gym = None
    for r in rows:
        if r["gym"] != cur_gym:
            cur_gym = r["gym"]
            print(f"\n🏋️ {cur_gym}:")
        print(f"   {r['exercise']}: {r['weight']}lb × {r['reps']} × {r['sets']}")
    conn.close()


def show_summary(days: int = 7):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    since = (datetime.now().replace(hour=0, minute=0, second=0) - __import__('datetime').timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT date, gym, exercise, weight, reps, sets 
        FROM workouts WHERE date >= ? ORDER BY date DESC, id
    """, (since,)).fetchall()
    if not rows:
        print(f"no workouts in last {days} days")
        return
    cur_date = None
    for r in rows:
        if r["date"] != cur_date:
            cur_date = r["date"]
            print(f"\n📅 {cur_date} — {r['gym']}")
        print(f"   {r['exercise']}: {r['weight']}lb × {r['reps']} × {r['sets']}")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_today()
    elif sys.argv[1] == "today":
        show_today()
    elif sys.argv[1] == "summary":
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
        show_summary(days)
    elif sys.argv[1] == "log" and len(sys.argv) >= 3:
        # First arg after 'log' is gym name, rest is exercises
        gym = sys.argv[2]
        raw = " ".join(sys.argv[3:])
        entries = parse_workout(raw)
        if not entries:
            print(f"could not parse: {raw}")
            print("format: log <gym> <exercise> <weight>x<reps>[x<sets>] ...")
            print("e.g.: log office bench 135x10x3 squat 185x5x3")
            sys.exit(1)
        new_prs = log_workout(gym, entries)
        print(f"✅ logged {len(entries)} exercises to {gym}")
        if new_prs:
            print(f"🏆 {len(new_prs)} new PR(s)!")
            for ex, g, w, r, e1rm in new_prs:
                print(f"   {ex} ({g}): {w}lb × {r} → est 1RM {e1rm}lb")
        show_today()
    elif sys.argv[1] == "prs":
        gym = sys.argv[2] if len(sys.argv) >= 3 else None
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        if gym:
            rows = conn.execute("SELECT * FROM prs WHERE gym=? ORDER BY exercise", (gym,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM prs ORDER BY gym, exercise").fetchall()
        conn.close()
        if not rows:
            print("no PRs yet — go lift")
        else:
            for r in rows:
                print(f"  {r['exercise']} ({r['gym']}): {r['weight']}lb × {r['reps']} → est 1RM {r['estimated_1rm']}lb ({r['achieved_at']})")
    elif sys.argv[1] == "help":
        print("""workout.py [command]
  today              — show today's workout
  summary [N]        — last N days summary
  log <gym> <data>   — log workout
                       format: exercise weightxreps[xsets]
                       e.g.: log office bench 135x10x3 squat 185x5x3
                       use BW or bw for bodyweight exercises
                       e.g.: log home pullup bw x 8 x 3""")
    else:
        print(f"unknown: {' '.join(sys.argv[1:])}")
