#!/usr/bin/env python3
"""Schedule manager — CLI wrapper around samos.schedule."""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Make repo-root importable when run from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from samos import schedule


def show_day():
    schedule.ensure_today()
    view = schedule.get_today_view()
    if not view:
        print(f"📅 {schedule.today_date()} — nothing scheduled")
        return
    print(f"📅 {schedule.today_date()} (living schedule)")
    for r in view:
        lock = "🔒" if r["fixed"] else "🔓"
        status_icon = {"pending": "⏳", "done": "✅", "skipped": "❌"}.get(r["status"], "·")
        marker = ""
        if r["status"] == "skipped":
            marker = f" — {r['reason'] or 'skipped'}"
        elif r["status"] == "done":
            marker = " ✓"
        print(
            f"  {r.get('color', '')} {r['effective_time']}  {r['name']:<25} "
            f"{r['duration_min']}min  {status_icon} {lock}{marker}"
        )


def show_week():
    week = schedule.template_week()
    for name, tasks in week.items():
        print(f"  {name.upper()}")
        for t in tasks:
            print(f"    {t['time_start']}  {t['name']}")
        if not tasks:
            print("    (free)")


def reschedule(task_name: str, new_day: str, permanent: bool = False):
    if permanent:
        result = schedule.template_reschedule(task_name, new_day)
        print(f"🔁 permanently moved '{result['name']}' from {result['from']} → {result['to']}")
    else:
        result = schedule.push_task(task_name, new_day)
        print(
            f"✅ moved '{result['task_name']}' to {new_day} ({result['target_date']}) — one-off"
        )


def log_completion(task_name: str, completed: bool, reason: str = ""):
    if completed:
        row = schedule.mark_done(task_name)
        print(f"✅ logged: {row['name']} — done")
    else:
        row = schedule.mark_skip(task_name, reason or "skipped")
        print(f"❌ logged: {row['name']} — skipped ({reason})")


def show_history(days: int = 7):
    rows = schedule.week_history(days)
    if not rows:
        print("no history yet")
        return
    cur = None
    for r in rows:
        if r["date"] != cur:
            cur = r["date"]
            print(f"\n📅 {cur}")
        status_icon = {"done": "✅", "skipped": "❌", "moved": "➡️", "pending": "⏳"}.get(
            r["status"], "·"
        )
        reason = f" — {r['reason']}" if r["reason"] else ""
        moved = f" → {r['moved_to']}" if r["moved_to"] else ""
        print(f"  {status_icon} {r['name']}{reason}{moved}")


def show_stats(days: int = 7):
    rows = schedule.stats(days)
    if not rows:
        print("no data yet")
        return
    print(f"\n📊 last {days} days:")
    for r in rows:
        done = r["done"] or 0
        skp = r["skipped"] or 0
        mov = r["moved"] or 0
        tot = r["total"]
        pct = (done / tot * 100) if tot else 0
        print(
            f"  {r['category']:<12} {done}/{tot} done ({pct:.0f}%)  {skp} skipped  {mov} moved"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_day()
    elif sys.argv[1] == "today" or sys.argv[1] == "when":
        show_day()
    elif sys.argv[1] == "week":
        show_week()
    elif sys.argv[1] == "push" and len(sys.argv) >= 4:
        permanent = "--permanent" in sys.argv
        args = [a for a in sys.argv[2:] if a != "--permanent"]
        reschedule(args[0], args[1], permanent=permanent)
    elif sys.argv[1] == "did" and len(sys.argv) >= 3:
        log_completion(sys.argv[2], True)
    elif sys.argv[1] == "skip" and len(sys.argv) >= 3:
        reason = " ".join(sys.argv[3:]) if len(sys.argv) >= 4 else "skipped"
        log_completion(sys.argv[2], False, reason)
    elif sys.argv[1] == "history":
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
        show_history(days)
    elif sys.argv[1] == "stats":
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
        show_stats(days)
    elif sys.argv[1] == "help":
        print(
            """schedule.py [command]
  (none)           — show today (living instances)
  today | when     — show today
  week             — show full template week
  push <task> <day>              — move today's instance (one-off)
  push <task> <day> --permanent  — rewrite the template (forever)
  did <task>       — mark task completed today
  skip <task> [reason] — mark skipped
  history [N]      — last N days of logs
  stats [N]        — completion stats by category"""
        )
    else:
        print(f"unknown: {' '.join(sys.argv[1:])}")
        print("use 'help'")
