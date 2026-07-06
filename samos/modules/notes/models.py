"""Notes and journal domain logic."""

from __future__ import annotations

from datetime import datetime, timedelta

from samos.db import NotFoundError, ValidationError, get_conn


def _now() -> str:
    return datetime.now().isoformat()


def add_note(title: str | None, body: str, tags: list[str] | None = None) -> dict:
    """Add a note."""
    body = body.strip()
    if not body:
        raise ValidationError("note body cannot be empty")
    with get_conn() as c:
        c.execute(
            "INSERT INTO notes (title, body, tags) VALUES (?, ?, ?)",
            (title, body, ",".join(tags) if tags else None),
        )
        note_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": note_id, "title": title, "body": body}


def search_notes(query: str, limit: int = 20) -> list[dict]:
    """Search notes by title/body/tags substring."""
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR body LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_notes(limit: int = 50) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_note(note_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not row:
        raise NotFoundError(f"no note with id {note_id}", {"id": note_id})
    return dict(row)


def update_note(note_id: int, title: str | None = None, body: str | None = None, tags: list[str] | None = None) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no note with id {note_id}", {"id": note_id})
        updates = {"updated_at": _now()}
        if title is not None:
            updates["title"] = title
        if body is not None:
            updates["body"] = body.strip()
        if tags is not None:
            updates["tags"] = ",".join(tags)
        if len(updates) > 1:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE notes SET {set_clause} WHERE id=?", (*updates.values(), note_id))
    return get_note(note_id)


def delete_note(note_id: int) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if not row:
            raise NotFoundError(f"no note with id {note_id}", {"id": note_id})
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))
    return {"deleted": dict(row)}


def add_journal_entry(date: str, entry: str, mood: int | None = None) -> dict:
    """Add or update a journal entry for a date."""
    entry = entry.strip()
    if not entry:
        raise ValidationError("journal entry cannot be empty")
    if mood is not None and not 1 <= mood <= 10:
        raise ValidationError("mood must be 1-10", {"value": mood})
    with get_conn() as c:
        existing = c.execute("SELECT id FROM journal WHERE date=?", (date,)).fetchone()
        if existing:
            c.execute(
                "UPDATE journal SET entry=?, mood=?, updated_at=? WHERE id=?",
                (entry, mood, _now(), existing["id"]),
            )
            entry_id = existing["id"]
        else:
            c.execute(
                "INSERT INTO journal (date, entry, mood) VALUES (?, ?, ?)",
                (date, entry, mood),
            )
            entry_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": entry_id, "date": date, "mood": mood}


def get_journal_entry(date: str) -> dict | None:
    with get_conn() as c:
        row = c.execute("SELECT * FROM journal WHERE date=?", (date,)).fetchone()
    return dict(row) if row else None


def journal_history(days: int = 7) -> list[dict]:
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM journal WHERE date >= ? ORDER BY date",
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]
