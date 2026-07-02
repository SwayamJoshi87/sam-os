#!/usr/bin/env python3
"""Schedule manager — show today, reschedule (one-off or permanent), log completions."""

import sqlite3, sys, re
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "/home/server/.hermes/scripts")
from schedule_lib import (
    DAYS, conn, today_date, dow_today,
    instantiate_day, get_today_view, mark_done, mark_skip,
    move_task, template_reschedule, find_target_date,
    week_history, stats,
)


def show_day():
    """Show today's living schedule (instances + status)."""
    # Auto-instantiate if empty (e.g. script ran before 8am cron)
    instantiate_day(today_date(), dow_today(), source="schedule.py-fallback")
    view = get_today_view()
    if not view:
        print(f"📅 {today_date()} — nothing scheduled")
        return
    print(f"📅 {today_date()} (living schedule)")
    for r in view:
        lock = "🔒" if r["fixed"] else "🔓"
        status_icon = {"pending": "⏳", "done": "✅", "skipped": "❌"}.get(r["status"], "·")
        time = r["effective_time"]
        marker = ""
        if r["status"] == "skipped":
            marker = f" — {r['reason'] or 'skipped'}"
        elif r["status"] == "done":
            marker = " ✓"
        print(f"  {r['color']} {time}  {r['name']:<25} {r['duration_min']}min  {status_icon} {lock}{marker}")


def show_week():
    """Show full template week (read from tasks table)."""
    c = conn()
    for dow in range(7):
        name = DAYS[dow]
        rows = c.execute("""
            SELECT t.id, c.name AS cat, t.name, t.time_start, t.duration_min
            FROM tasks t JOIN categories c ON t.category_id=c.id
            WHERE t.day_of_week=? ORDER BY t.time_start
        """, (dow,)).fetchall()
        print(f"  {name.upper()}")
        for r in rows:
            print(f"    {r['time_start']}  {r['name']}")
        if not rows:
            print("    (free)")
    c.close()


def reschedule(task_name: str, new_day: str, permanent: bool = False):
    """Push a task.

    Default: one-off — moves today's instance only, template untouched.
    --permanent: rewrites the template.
    """
    if permanent:
        result = template_reschedule(task_name, new_day)
        if not result:
            print(f"unknown day '{new_day}' or no task matching '{task_name}'")
            return
        print(f"🔁 permanently moved '{result['name']}' from {result['from']} → {result['to']}")
    else:
        target_date = find_target_date(new_day)
        if not target_date:
            print(f"unknown day: {new_day}. use mon/tue/wed/thu/fri/sat/sun")
            return
        result = move_task(task_name, target_date, reason=f"pushed to {new_day}")
        if result:
            print(f"✅ moved '{result['task_name']}' to {new_day} ({target_date}) — one-off, template unchanged")
        else:
            print(f"no pending '{task_name}' today to move")


def log_completion(task_name: str, completed: bool, reason: str = ""):
    """Log whether a task was done today."""
    if completed:
        row = mark_done(task_name)
        if row:
            print(f"✅ logged: {row['name']} — done")
        else:
            print(f"no pending '{task_name}' today")
    else:
        row = mark_skip(task_name, reason or "skipped")
        if row:
            print(f"❌ logged: {row['name']} — skipped ({reason})")
        else:
            print(f"no pending '{task_name}' today")


def show_history(days: int = 7):
    """Show completion log."""
    rows = week_history(days)
    if not rows:
        print("no history yet")
        return
    cur = None
    for r in rows:
        if r["date"] != cur:
            cur = r["date"]
            print(f"\n📅 {cur}")
        status_icon = {"done": "✅", "skipped": "❌", "moved": "➡️", "pending": "⏳"}.get(r["status"], "·")
        reason = f" — {r['reason']}" if r["reason"] else ""
        moved = f" → {r['moved_to']}" if r["moved_to"] else ""
        print(f"  {status_icon} {r['name']}{reason}{moved}")


def show_stats(days: int = 7):
    """Completion stats by category."""
    rows = stats(days)
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
        print(f"  {r['category']:<12} {done}/{tot} done ({pct:.0f}%)  {skp} skipped  {mov} moved")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_day()
    elif sys.argv[1] == "today":
        show_day()
    elif sys.argv[1] == "when":
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
        print("""schedule.py [command]
  (none)           — show today (living instances)
  today | when     — show today
  week             — show full template week
  push <task> <day>              — move today's instance (one-off)
  push <task> <day> --permanent  — rewrite the template (forever)
  did <task>       — mark task completed today
  skip <task> [reason] — mark skipped
  history [N]      — last N days of logs
  stats [N]        — completion stats by category""")
    else:
        print(f"unknown: {' '.join(sys.argv[1:])}")
        print("use 'help'")