"""Shared schedule helpers — template + today_instances with ad-hoc edits."""

import re
from datetime import datetime, timedelta

from .db import ConflictError, NotFoundError, ValidationError, get_conn

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_MAP = {}
for i, n in enumerate(DAYS):
    DAY_MAP[n] = i
    DAY_MAP[n + "day"] = i

VALID_STATUSES = {"pending", "done", "skipped", "moved"}
TIME_RE = re.compile(r"^([0-1]?\d|2[0-3]):([0-5]\d)$")


def _validate_day(day: str) -> int:
    d = day.lower().strip()
    if d not in DAY_MAP:
        raise ValidationError(
            f"unknown day '{day}'",
            {"valid_days": sorted(set(DAY_MAP.keys()))},
        )
    return DAY_MAP[d]


def _validate_time(time_str: str) -> str:
    t = time_str.strip()
    if not TIME_RE.match(t):
        raise ValidationError(
            f"invalid time '{time_str}'",
            {"expected_format": "HH:MM", "example": "09:30"},
        )
    return f"{int(t.split(':')[0]):02d}:{int(t.split(':')[1]):02d}"


def _category_id(category_name: str, conn) -> int:
    row = conn.execute(
        "SELECT id FROM categories WHERE name LIKE ?", (f"%{category_name}%",)
    ).fetchone()
    if not row:
        raise NotFoundError(
            f"no category matching '{category_name}'",
            {"category": category_name},
        )
    return row["id"]


def today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def dow_today() -> int:
    return datetime.now().weekday()


def day_name(dow: int) -> str:
    return DAYS[dow]


def instantiate_day(date_str: str, dow: int, source: str = "cron") -> int:
    """Copy template tasks for `dow` into today_instances for `date_str`.

    Idempotent — UNIQUE(date, task_id) prevents dupes.
    Returns count of new rows created.
    """
    with get_conn() as c:
        cur = c.execute(
            """
            INSERT OR IGNORE INTO today_instances (date, task_id, status, source)
            SELECT ?, id, 'pending', ? FROM tasks WHERE day_of_week = ?
            """,
            (date_str, source, dow),
        )
    return cur.rowcount


def ensure_today() -> list[dict]:
    """Instantiate today from template if missing, then return living schedule."""
    d = today_date()
    with get_conn() as c:
        existing = c.execute(
            "SELECT COUNT(*) AS n FROM today_instances WHERE date=?", (d,)
        ).fetchone()["n"]
        if existing == 0:
            instantiate_day(d, dow_today(), source="auto")
    return get_today_view()


def get_today_view() -> list[dict]:
    """Return today's effective schedule: instances joined to tasks."""
    with get_conn() as c:
        rows = c.execute(
            """
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
            """,
            (today_date(),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_pending_tasks() -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT i.id, t.name, c.name AS category
            FROM today_instances i
            JOIN tasks t ON i.task_id = t.id
            JOIN categories c ON t.category_id = c.id
            WHERE i.date = ? AND i.status = 'pending'
            """,
            (today_date(),),
        ).fetchall()
    return [dict(r) for r in rows]


def _find_pending_instance(task_name: str, c):
    row = c.execute(
        """
        SELECT i.id, t.name FROM today_instances i
        JOIN tasks t ON i.task_id = t.id
        WHERE i.date = ? AND i.status = 'pending' AND t.name LIKE ?
        LIMIT 1
        """,
        (today_date(), f"%{task_name}%"),
    ).fetchone()
    if not row:
        raise NotFoundError(
            f"no pending task matching '{task_name}' today",
            {"task": task_name, "date": today_date()},
        )
    return row


def mark_done(task_name: str, reason: str = "") -> dict:
    with get_conn() as c:
        row = _find_pending_instance(task_name, c)
        c.execute(
            """
            UPDATE today_instances SET status='done', completed_at=CURRENT_TIMESTAMP, reason=?
            WHERE id=?
            """,
            (reason, row["id"]),
        )
    return dict(row)


def mark_skip(task_name: str, reason: str = "skipped") -> dict:
    with get_conn() as c:
        row = _find_pending_instance(task_name, c)
        c.execute(
            "UPDATE today_instances SET status='skipped', reason=? WHERE id=?",
            (reason, row["id"]),
        )
    return dict(row)


def _find_target_date(target_day: str) -> str:
    target_dow = _validate_day(target_day)
    today_dow = dow_today()
    delta = (target_dow - today_dow) % 7
    if delta == 0:
        delta = 7
    return (datetime.now() + timedelta(days=delta)).strftime("%Y-%m-%d")


def move_task(task_name: str, target_date: str, new_time: str | None = None, reason: str = "") -> dict:
    """Move a pending task instance to a future date."""
    _validate_time(new_time) if new_time else None
    with get_conn() as c:
        row = _find_pending_instance(task_name, c)
        c.execute(
            """
            UPDATE today_instances SET status='moved', moved_to=?, reason=?, new_time=?
            WHERE id=?
            """,
            (target_date, reason, new_time, row["id"]),
        )
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        target_dow = target_dt.weekday()
        c.execute(
            """
            INSERT OR IGNORE INTO today_instances (date, task_id, status, source)
            SELECT ?, id, 'pending', 'manual' FROM tasks WHERE day_of_week = ?
            """,
            (target_date, target_dow),
        )
        c.execute(
            """
            INSERT INTO today_instances (date, task_id, status, source, new_time)
            VALUES (?, ?, 'pending', 'telegram', ?)
            """,
            (target_date, row["task_id"], new_time),
        )
        new_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {
        "moved_from": today_date(),
        "new_instance_id": new_id,
        "task_name": row["name"],
        "target_date": target_date,
    }


def push_task(task_name: str, day: str, permanent: bool = False) -> dict:
    if permanent:
        return template_reschedule(task_name, day)
    target = _find_target_date(day)
    return move_task(task_name, target, reason=f"pushed to {day}")


def add_today_task(
    task_name: str,
    category: str,
    time_start: str,
    duration_min: int,
    source: str = "manual",
) -> dict:
    """Add an ad-hoc task to today's living schedule without touching the template."""
    if not task_name.strip():
        raise ValidationError("task_name cannot be empty")
    if duration_min <= 0:
        raise ValidationError("duration_min must be positive", {"value": duration_min})
    time_start = _validate_time(time_start)

    with get_conn() as c:
        cat_id = _category_id(category, c)
        # Check for overlap with fixed tasks on today
        end = (
            datetime.strptime(time_start, "%H:%M") + timedelta(minutes=duration_min)
        ).strftime("%H:%M")
        overlap = c.execute(
            """
            SELECT t.name, t.time_start, t.duration_min
            FROM today_instances i
            JOIN tasks t ON i.task_id = t.id
            WHERE i.date = ? AND i.status = 'pending' AND t.fixed = 1
              AND t.time_start < ? AND datetime(t.time_start, '+' || t.duration_min || ' minutes') > ?
            """,
            (today_date(), end, time_start),
        ).fetchone()
        if overlap:
            raise ConflictError(
                f"ad-hoc task overlaps fixed task '{overlap['name']}'",
                {
                    "overlap": dict(overlap),
                    "requested": {"time_start": time_start, "duration_min": duration_min},
                },
            )

        # Insert a backing task row with day_of_week = -1 so it never appears
        # in the weekly template, only in today's instances.
        c.execute(
            """
            INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed)
            VALUES (?, ?, -1, ?, ?, 0)
            """,
            (cat_id, task_name, time_start, duration_min),
        )
        task_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute(
            """
            INSERT INTO today_instances (date, task_id, status, source, new_time)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (today_date(), task_id, source, time_start),
        )
        instance_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]

    return {
        "task_id": task_id,
        "instance_id": instance_id,
        "name": task_name,
        "date": today_date(),
        "time": time_start,
        "duration_min": duration_min,
    }


def remove_today_task(task_name_or_id: str | int, reason: str = "removed by user") -> dict:
    """Remove a pending/remaining task from today's living schedule."""
    with get_conn() as c:
        if isinstance(task_name_or_id, int):
            row = c.execute(
                """
                SELECT i.id, t.name FROM today_instances i
                JOIN tasks t ON i.task_id = t.id
                WHERE i.id = ? AND i.date = ? AND i.status != 'moved'
                """,
                (task_name_or_id, today_date()),
            ).fetchone()
        else:
            row = c.execute(
                """
                SELECT i.id, t.name FROM today_instances i
                JOIN tasks t ON i.task_id = t.id
                WHERE i.date = ? AND i.status != 'moved' AND t.name LIKE ?
                LIMIT 1
                """,
                (today_date(), f"%{task_name_or_id}%"),
            ).fetchone()
        if not row:
            raise NotFoundError(
                f"no removable task matching '{task_name_or_id}' today",
                {"task": task_name_or_id, "date": today_date()},
            )
        c.execute(
            "UPDATE today_instances SET status='skipped', reason=? WHERE id=?",
            (reason, row["id"]),
        )
    return {"removed": dict(row), "reason": reason}


def retime_today_task(task_name_or_id: str | int, new_time: str) -> dict:
    """Change the time of a task already instantiated for today."""
    new_time = _validate_time(new_time)
    with get_conn() as c:
        if isinstance(task_name_or_id, int):
            row = c.execute(
                """
                SELECT i.id, t.name, t.duration_min, t.fixed FROM today_instances i
                JOIN tasks t ON i.task_id = t.id
                WHERE i.id = ? AND i.date = ? AND i.status = 'pending'
                """,
                (task_name_or_id, today_date()),
            ).fetchone()
        else:
            row = c.execute(
                """
                SELECT i.id, t.name, t.duration_min, t.fixed FROM today_instances i
                JOIN tasks t ON i.task_id = t.id
                WHERE i.date = ? AND i.status = 'pending' AND t.name LIKE ?
                LIMIT 1
                """,
                (today_date(), f"%{task_name_or_id}%"),
            ).fetchone()
        if not row:
            raise NotFoundError(
                f"no pending task matching '{task_name_or_id}' today",
                {"task": task_name_or_id, "date": today_date()},
            )
        c.execute(
            "UPDATE today_instances SET new_time=? WHERE id=?",
            (new_time, row["id"]),
        )
    return {"task": dict(row), "new_time": new_time}


def end_of_day_sweep() -> int:
    """Mark all still-pending instances for today as skipped."""
    with get_conn() as c:
        cur = c.execute(
            """
            UPDATE today_instances SET status='skipped', reason='end of day — no response'
            WHERE date = ? AND status = 'pending'
            """,
            (today_date(),),
        )
    return cur.rowcount


def week_history(days: int = 7) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT i.date, t.name, c.name AS category, c.color,
                   i.status, i.completed_at, i.moved_to, i.reason, i.source
            FROM today_instances i
            JOIN tasks t ON i.task_id = t.id
            JOIN categories c ON t.category_id = c.id
            WHERE i.date >= ?
            ORDER BY i.date DESC, COALESCE(i.new_time, t.time_start)
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def stats(days: int = 7) -> list[dict]:
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
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
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def template_week() -> dict:
    out = {}
    with get_conn() as c:
        for dow in range(7):
            rows = c.execute(
                """
                SELECT t.id, c.name AS cat, t.name, t.time_start, t.duration_min, t.fixed
                FROM tasks t JOIN categories c ON t.category_id=c.id
                WHERE t.day_of_week=? ORDER BY t.time_start
                """,
                (dow,),
            ).fetchall()
            out[DAYS[dow]] = [dict(r) for r in rows]
    return out


def template_reschedule(task_name: str, new_day: str) -> dict:
    new_dow = _validate_day(new_day)
    with get_conn() as c:
        task = c.execute(
            "SELECT id, name, fixed, day_of_week FROM tasks WHERE name LIKE ? LIMIT 1",
            (f"%{task_name}%",),
        ).fetchone()
        if not task:
            raise NotFoundError(
                f"no task matching '{task_name}' in template",
                {"task": task_name},
            )
        if task["day_of_week"] < 0 or task["day_of_week"] > 6:
            raise ValidationError(
                f"'{task['name']}' is an ad-hoc task and cannot be moved via the weekly template",
                {"task": task["name"]},
            )
        old_dow = DAYS[task["day_of_week"]]
        c.execute("UPDATE tasks SET day_of_week=? WHERE id=?", (new_dow, task["id"]))
    return {"name": task["name"], "from": old_dow, "to": new_day.lower()}


def diff_today_vs_template() -> dict:
    """Show how today diverges from the template."""
    d = today_date()
    dow = dow_today()
    with get_conn() as c:
        template = c.execute(
            """
            SELECT t.id, t.name, t.time_start, t.duration_min, c.name AS category
            FROM tasks t JOIN categories c ON t.category_id = c.id
            WHERE t.day_of_week = ? ORDER BY t.time_start
            """,
            (dow,),
        ).fetchall()
        instances = c.execute(
            """
            SELECT t.name, COALESCE(i.new_time, t.time_start) AS time,
                   t.duration_min, c.name AS category, i.status, i.source
            FROM today_instances i
            JOIN tasks t ON i.task_id = t.id
            JOIN categories c ON t.category_id = c.id
            WHERE i.date = ? AND i.status != 'moved'
            ORDER BY time
            """,
            (d,),
        ).fetchall()
    return {
        "date": d,
        "template": [dict(r) for r in template],
        "today": [dict(r) for r in instances],
    }
