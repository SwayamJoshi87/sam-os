"""Projects domain logic."""

from __future__ import annotations

from datetime import datetime

from samos.db import NotFoundError, ValidationError, get_conn


def _now() -> str:
    return datetime.now().isoformat()


VALID_STATUSES = {"active", "paused", "completed", "archived"}


def add_project(name: str, description: str | None = None) -> dict:
    """Add a new project."""
    name = name.strip()
    if not name:
        raise ValidationError("project name cannot be empty")
    with get_conn() as c:
        try:
            c.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description),
            )
        except Exception:
            raise ValidationError(f"project '{name}' already exists", {"name": name})
        project_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": project_id, "name": name, "status": "active"}


def list_projects(status: str | None = None) -> list[dict]:
    with get_conn() as c:
        sql = "SELECT * FROM projects"
        params: list = []
        if status:
            if status not in VALID_STATUSES:
                raise ValidationError("invalid status", {"valid": sorted(VALID_STATUSES)})
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY updated_at DESC"
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise NotFoundError(f"no project with id {project_id}", {"id": project_id})
    return dict(row)


def update_project(project_id: int, name: str | None = None, description: str | None = None, status: str | None = None, notes: str | None = None) -> dict:
    if status is not None and status not in VALID_STATUSES:
        raise ValidationError("invalid status", {"valid": sorted(VALID_STATUSES)})
    with get_conn() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no project with id {project_id}", {"id": project_id})
        updates = {"updated_at": _now()}
        if name is not None:
            updates["name"] = name.strip()
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
        if notes is not None:
            updates["notes"] = notes
        if len(updates) > 1:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE projects SET {set_clause} WHERE id=?", (*updates.values(), project_id))
    return get_project(project_id)


def delete_project(project_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no project with id {project_id}", {"id": project_id})
        c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    return {"deleted": dict(row)}
