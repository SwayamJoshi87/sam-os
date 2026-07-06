"""Todo list domain logic."""

from __future__ import annotations

from datetime import datetime

from samos.db import NotFoundError, ValidationError, get_conn


def _now() -> str:
    return datetime.now().isoformat()


def add_todo(
    text: str,
    priority: int = 3,
    due_date: str | None = None,
    project_id: int | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Add a new todo."""
    text = text.strip()
    if not text:
        raise ValidationError("todo text cannot be empty")
    if not 1 <= priority <= 5:
        raise ValidationError("priority must be 1-5", {"value": priority})
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO todos (text, priority, due_date, project_id, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (text, priority, due_date, project_id, ",".join(tags) if tags else None),
        )
        todo_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": todo_id, "text": text, "status": "pending", "priority": priority}


def list_todos(status: str | None = None, limit: int = 100) -> list[dict]:
    """List todos, optionally filtered by status."""
    with get_conn() as c:
        sql = "SELECT * FROM todos"
        params: list = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY priority ASC, created_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_todo(todo_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
    if not row:
        raise NotFoundError(f"no todo with id {todo_id}", {"id": todo_id})
    return dict(row)


def complete_todo(todo_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no todo with id {todo_id}", {"id": todo_id})
        c.execute(
            "UPDATE todos SET status='done', completed_at=? WHERE id=?",
            (_now(), todo_id),
        )
    return dict(row) | {"status": "done", "completed_at": _now()}


def cancel_todo(todo_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no todo with id {todo_id}", {"id": todo_id})
        c.execute("UPDATE todos SET status='cancelled' WHERE id=?", (todo_id,))
    return dict(row) | {"status": "cancelled"}


def update_todo(
    todo_id: int,
    text: str | None = None,
    priority: int | None = None,
    due_date: str | None = None,
    project_id: int | None = None,
    tags: list[str] | None = None,
) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no todo with id {todo_id}", {"id": todo_id})
        updates = {}
        if text is not None:
            updates["text"] = text.strip()
        if priority is not None:
            if not 1 <= priority <= 5:
                raise ValidationError("priority must be 1-5", {"value": priority})
            updates["priority"] = priority
        if due_date is not None:
            updates["due_date"] = due_date
        if project_id is not None:
            updates["project_id"] = project_id
        if tags is not None:
            updates["tags"] = ",".join(tags)
        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE todos SET {set_clause} WHERE id=?", (*updates.values(), todo_id))
    return get_todo(todo_id)


def delete_todo(todo_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no todo with id {todo_id}", {"id": todo_id})
        c.execute("DELETE FROM todos WHERE id=?", (todo_id,))
    return {"deleted": dict(row)}


def todos_today() -> dict:
    """Return todos due today or overdue."""
    d = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT * FROM todos
            WHERE status='pending' AND (due_date IS NULL OR due_date <= ?)
            ORDER BY priority ASC, created_at DESC
            """,
            (d,),
        ).fetchall()
    return {"date": d, "todos": [dict(r) for r in rows]}
