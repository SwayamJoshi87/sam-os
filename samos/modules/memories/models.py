"""Memories and user facts domain logic."""

from __future__ import annotations

from datetime import datetime

from samos.db import NotFoundError, ValidationError, get_conn


def _now() -> str:
    return datetime.now().isoformat()


def remember(category: str, fact: str, confidence: int = 5, source: str | None = None) -> dict:
    """Store a fact the agent should remember."""
    category = category.strip().lower()
    fact = fact.strip()
    if not category:
        raise ValidationError("category cannot be empty")
    if not fact:
        raise ValidationError("fact cannot be empty")
    if not 1 <= confidence <= 10:
        raise ValidationError("confidence must be 1-10", {"value": confidence})
    with get_conn() as c:
        c.execute(
            "INSERT INTO memories (category, fact, confidence, source) VALUES (?, ?, ?, ?)",
            (category, fact, confidence, source),
        )
        memory_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": memory_id, "category": category, "fact": fact}


def recall(category: str | None = None, query: str | None = None, limit: int = 50) -> list[dict]:
    """Recall memories, optionally filtered by category or search query."""
    with get_conn() as c:
        sql = "SELECT * FROM memories"
        params: list = []
        conditions = []
        if query:
            conditions.append("(fact LIKE ? OR category LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("category=?")
            params.append(category)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_memory(memory_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
    if not row:
        raise NotFoundError(f"no memory with id {memory_id}", {"id": memory_id})
    return dict(row)


def update_memory(memory_id: int, fact: str | None = None, confidence: int | None = None, source: str | None = None) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no memory with id {memory_id}", {"id": memory_id})
        updates = {"updated_at": _now()}
        if fact is not None:
            updates["fact"] = fact.strip()
        if confidence is not None:
            if not 1 <= confidence <= 10:
                raise ValidationError("confidence must be 1-10", {"value": confidence})
            updates["confidence"] = confidence
        if source is not None:
            updates["source"] = source
        if len(updates) > 1:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE memories SET {set_clause} WHERE id=?", (*updates.values(), memory_id))
    return get_memory(memory_id)


def forget(memory_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no memory with id {memory_id}", {"id": memory_id})
        c.execute("DELETE FROM memories WHERE id=?", (memory_id,))
    return {"deleted": dict(row)}
