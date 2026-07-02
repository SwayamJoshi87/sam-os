"""Shared schedule helpers — read instances-first, fall back to template."""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Honour SAMOS_DB_PATH if set (api container), otherwise default to host path (CLI)
DB = Path(os.environ.get("SAMOS_DB_PATH", "/home/server/data/schedule.db"))
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def conn():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


def today_date():
    return datetime.now().strftime("%Y-%m-%d")


def dow_today():
    return datetime.now().weekday()


def day_name(dow):
    return DAYS[dow]


def instantiate_day(date_str, dow, source="cron"):
    """Copy template tasks for `dow` into today_instances for `date_str`.

    Idempotent — UNIQUE(date, task_id) prevents dupes.
    Returns count of new rows created.
    """
    c = conn()
    cur = c.execute("""
        INSERT OR IGNORE INTO today_instances (date, task_id, status, source)
        SELECT ?, id, 'pending', ? FROM tasks WHERE day_of_week = ?
    """, (date_str, source, dow))
    c.commit()
    n = cur.rowcount
    c.close()
    return n


def get_today_view():
    """Return today's effective schedule: instances joined to tasks, with overrides applied.

    Skips status='moved' rows (those are *from* here, not *at* here).
    Returns list of dicts.
    """
    c = conn()
    rows = c.execute("""
        SELECT i.id, i.task_id, t.name, t.duration_min, t.fixed,
               c.name AS category, c.color,
               i.status, i.completed_at, i.moved_to, i.new_time, i.reason, i.source,
               COALESCE(i.new_time, t.time_start) AS effective_time
        FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE i.date = ?
          AND i.status != 'moved'
        ORDER BY effective_time
    """, (today_date(),)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_pending_tasks():
    """Tasks for today that are still pending."""
    c = conn()
    rows = c.execute("""
        SELECT i.id, t.name, c.name AS category
        FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE i.date = ? AND i.status = 'pending'
    """, (today_date(),)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def mark_done(task_name, reason=""):
    """Mark today's pending instance matching task_name as done."""
    c = conn()
    row = c.execute("""
        SELECT i.id, t.name FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        WHERE i.date = ? AND i.status = 'pending' AND t.name LIKE ?
        LIMIT 1
    """, (today_date(), f"%{task_name}%")).fetchone()
    if not row:
        c.close()
        return None
    c.execute("""
        UPDATE today_instances SET status='done', completed_at=CURRENT_TIMESTAMP, reason=?
        WHERE id=?
    """, (reason, row["id"]))
    c.commit()
    c.close()
    return dict(row)


def mark_skip(task_name, reason):
    """Mark today's pending instance matching task_name as skipped."""
    c = conn()
    row = c.execute("""
        SELECT i.id, t.name FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        WHERE i.date = ? AND i.status = 'pending' AND t.name LIKE ?
        LIMIT 1
    """, (today_date(), f"%{task_name}%")).fetchone()
    if not row:
        c.close()
        return None
    c.execute("""
        UPDATE today_instances SET status='skipped', reason=?
        WHERE id=?
    """, (reason, row["id"]))
    c.commit()
    c.close()
    return dict(row)


def move_task(task_name, target_date, new_time=None, reason=""):
    """Mark today's instance as moved, create a new pending instance on target_date."""
    c = conn()
    row = c.execute("""
        SELECT i.id, i.task_id, t.day_of_week, t.name FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        WHERE i.date = ? AND i.status = 'pending' AND t.name LIKE ?
        LIMIT 1
    """, (today_date(), f"%{task_name}%")).fetchone()
    if not row:
        c.close()
        return None
    c.execute("""
        UPDATE today_instances SET status='moved', moved_to=?, reason=?, new_time=?
        WHERE id=?
    """, (target_date, reason, new_time, row["id"]))
    # create instance on target date — reuse same connection to avoid lock
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    target_dow = target_dt.weekday()
    # inline instantiate for target date on the same connection
    c.execute("""
        INSERT OR IGNORE INTO today_instances (date, task_id, status, source)
        SELECT ?, id, 'pending', 'manual' FROM tasks WHERE day_of_week = ?
    """, (target_date, target_dow))
    c.execute("""
        INSERT INTO today_instances (date, task_id, status, source, new_time)
        VALUES (?, ?, 'pending', 'telegram', ?)
    """, (target_date, row["task_id"], new_time))
    new_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return {"moved_from": today_date(), "new_instance_id": new_id, "task_name": row["name"]}


def end_of_day_sweep():
    """Mark all still-pending instances for today as skipped."""
    c = conn()
    cur = c.execute("""
        UPDATE today_instances SET status='skipped', reason='end of day — no response'
        WHERE date = ? AND status = 'pending'
    """, (today_date(),))
    c.commit()
    n = cur.rowcount
    c.close()
    return n


def week_history(days=7):
    """Return recent history grouped by date."""
    c = conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = c.execute("""
        SELECT i.date, t.name, c.name AS category, c.color,
               i.status, i.completed_at, i.moved_to, i.reason, i.source
        FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE i.date >= ?
        ORDER BY i.date DESC, COALESCE(i.new_time, t.time_start)
    """, (since,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def stats(days=7):
    """Completion stats by category."""
    c = conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = c.execute("""
        SELECT c.name AS category,
               COUNT(*) AS total,
               SUM(CASE WHEN i.status='done' THEN 1 ELSE 0 END) AS done,
               SUM(CASE WHEN i.status='skipped' THEN 1 ELSE 0 END) AS skipped,
               SUM(CASE WHEN i.status='moved' THEN 1 ELSE 0 END) AS moved
        FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE i.date >= ?
        GROUP BY c.name
        ORDER BY c.name
    """, (since,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def template_reschedule(task_name, new_day):
    """Rewrite the template (tasks table). Used for permanent moves only."""
    short = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    full = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_to_dow = {n: i for i, n in enumerate(short)}
    day_to_dow.update({n: i for i, n in enumerate(full)})
    target = new_day.lower().strip()
    if target not in day_to_dow:
        return None
    new_dow = day_to_dow[target]
    c = conn()
    task = c.execute(
        "SELECT id, name, fixed, day_of_week FROM tasks WHERE name LIKE ? LIMIT 1",
        (f"%{task_name}%",)
    ).fetchone()
    if not task:
        c.close()
        return None
    old_dow = DAYS[task["day_of_week"]]
    c.execute("UPDATE tasks SET day_of_week=? WHERE id=?", (new_dow, task["id"]))
    c.commit()
    c.close()
    return {"name": task["name"], "from": old_dow, "to": new_day.lower()}


def find_target_date(target_day):
    """Given a day name (mon..sun OR monday..sunday), return next YYYY-MM-DD for that weekday."""
    short = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    full = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_to_dow = {n: i for i, n in enumerate(short)}
    day_to_dow.update({n: i for i, n in enumerate(full)})
    target = target_day.lower().strip()
    if target not in day_to_dow:
        return None
    target_dow = day_to_dow[target]
    today_dow = dow_today()
    delta = (target_dow - today_dow) % 7
    if delta == 0:
        delta = 7
    return (datetime.now() + timedelta(days=delta)).strftime("%Y-%m-%d")