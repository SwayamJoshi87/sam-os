"""Productivity helpers: habits, shopping list, away mode, task notes."""

from __future__ import annotations

from datetime import datetime, timedelta

from .db import NotFoundError, ValidationError, get_conn


def _date_str(d: datetime | None = None) -> str:
    return (d or datetime.now()).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Habits
# ---------------------------------------------------------------------------

def add_habit(name: str, description: str | None = None) -> dict:
    """Create a new daily habit."""
    name = name.strip().lower()
    if not name:
        raise ValidationError("habit name cannot be empty")
    with get_conn() as c:
        c.execute(
            "INSERT INTO habits (name, description) VALUES (?, ?)",
            (name, description),
        )
        habit_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": habit_id, "name": name, "description": description}


def list_habits() -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, name, description, active FROM habits ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def log_habit(habit_name: str, status: str, date: str | None = None, note: str | None = None) -> dict:
    """Mark a habit done or missed for a date."""
    if status not in {"done", "missed"}:
        raise ValidationError("status must be 'done' or 'missed'", {"value": status})
    d = date or _date_str()
    with get_conn() as c:
        habit = c.execute(
            "SELECT id FROM habits WHERE name LIKE ? AND active=1",
            (f"%{habit_name}%",),
        ).fetchone()
        if not habit:
            raise NotFoundError(f"no active habit matching '{habit_name}'", {"habit": habit_name})
        c.execute(
            """
            INSERT INTO habit_logs (habit_id, date, status, note)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(habit_id, date) DO UPDATE SET status=excluded.status,
                                                       note=excluded.note,
                                                       logged_at=CURRENT_TIMESTAMP
            """,
            (habit["id"], d, status, note),
        )
    return {"habit": habit_name, "date": d, "status": status, "note": note}


def habits_today(date: str | None = None) -> dict:
    """Return all habits and today's status."""
    d = date or _date_str()
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT h.id, h.name, h.description,
                   COALESCE(l.status, 'pending') AS status,
                   l.note
            FROM habits h
            LEFT JOIN habit_logs l ON l.habit_id=h.id AND l.date=?
            WHERE h.active=1
            ORDER BY h.name
            """,
            (d,),
        ).fetchall()
    return {"date": d, "habits": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Shopping list
# ---------------------------------------------------------------------------

def add_shopping_item(item: str, category: str | None = None) -> dict:
    """Add an item to the shopping list."""
    item = item.strip()
    if not item:
        raise ValidationError("item cannot be empty")
    with get_conn() as c:
        c.execute(
            "INSERT INTO shopping_items (item, category) VALUES (?, ?)",
            (item, category),
        )
        item_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": item_id, "item": item, "category": category, "purchased": 0}


def shopping_list(show_purchased: bool = False) -> dict:
    with get_conn() as c:
        sql = "SELECT * FROM shopping_items"
        if not show_purchased:
            sql += " WHERE purchased=0"
        sql += " ORDER BY category, item"
        rows = c.execute(sql).fetchall()
    return {"items": [dict(r) for r in rows]}


def mark_shopping_purchased(item_id: int, purchased: bool = True) -> dict:
    with get_conn() as c:
        c.execute(
            "UPDATE shopping_items SET purchased=? WHERE id=?",
            (1 if purchased else 0, item_id),
        )
        if c.rowcount == 0:
            raise NotFoundError(f"no shopping item with id {item_id}", {"id": item_id})
    return {"id": item_id, "purchased": purchased}


def clear_purchased_items() -> dict:
    with get_conn() as c:
        cur = c.execute("DELETE FROM shopping_items WHERE purchased=1")
    return {"cleared": cur.rowcount}


# ---------------------------------------------------------------------------
# Away mode
# ---------------------------------------------------------------------------

def add_away_dates(start_date: str, end_date: str, reason: str | None = None) -> dict:
    """Suppress today-instance creation for a date range."""
    if start_date > end_date:
        raise ValidationError("start_date must be <= end_date")
    with get_conn() as c:
        c.execute(
            "INSERT INTO away_dates (start_date, end_date, reason) VALUES (?, ?, ?)",
            (start_date, end_date, reason),
        )
        away_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": away_id, "start_date": start_date, "end_date": end_date, "reason": reason}


def list_away_dates() -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM away_dates ORDER BY start_date"
        ).fetchall()
    return [dict(r) for r in rows]


def is_away(date: str | None = None) -> dict:
    """Check whether a date falls inside an away range."""
    d = date or _date_str()
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM away_dates WHERE ? BETWEEN start_date AND end_date LIMIT 1",
            (d,),
        ).fetchone()
    return {"date": d, "away": row is not None, "details": dict(row) if row else None}


# ---------------------------------------------------------------------------
# Task notes
# ---------------------------------------------------------------------------

def add_task_note(task_name_or_id: str | int, note: str) -> dict:
    """Attach a note to today's instance of a task."""
    from .schedule import today_date

    d = today_date()
    with get_conn() as c:
        if isinstance(task_name_or_id, int):
            row = c.execute(
                """
                SELECT i.id, t.name FROM today_instances i
                JOIN tasks t ON i.task_id=t.id
                WHERE i.id=? AND i.date=? AND i.status!='moved'
                """,
                (task_name_or_id, d),
            ).fetchone()
        else:
            row = c.execute(
                """
                SELECT i.id, t.name FROM today_instances i
                JOIN tasks t ON i.task_id=t.id
                WHERE i.date=? AND i.status!='moved' AND t.name LIKE ?
                LIMIT 1
                """,
                (d, f"%{task_name_or_id}%"),
            ).fetchone()
        if not row:
            raise NotFoundError(
                f"no task matching '{task_name_or_id}' today",
                {"task": task_name_or_id, "date": d},
            )
        c.execute(
            "INSERT INTO task_notes (instance_id, note) VALUES (?, ?)",
            (row["id"], note),
        )
    return {"task": row["name"], "date": d, "note": note}


def task_notes(task_name_or_id: str | int | None = None, date: str | None = None) -> list[dict]:
    """Return notes for today's task instances, optionally filtered by task name/id."""
    from .schedule import today_date

    d = date or today_date()
    with get_conn() as c:
        sql = """
            SELECT t.name AS task_name, i.id AS instance_id, n.note, n.created_at
            FROM task_notes n
            JOIN today_instances i ON n.instance_id=i.id
            JOIN tasks t ON i.task_id=t.id
            WHERE i.date=?
        """
        params: list = [d]
        if isinstance(task_name_or_id, int):
            sql += " AND i.id=?"
            params.append(task_name_or_id)
        elif isinstance(task_name_or_id, str):
            sql += " AND t.name LIKE ?"
            params.append(f"%{task_name_or_id}%")
        sql += " ORDER BY n.created_at"
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
