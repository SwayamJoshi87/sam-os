"""User profile domain logic."""

from __future__ import annotations

from datetime import datetime

from samos.db import NotFoundError, ValidationError, get_conn


def _now() -> str:
    return datetime.now().isoformat()


def set_profile(key: str, value: str | int | float | dict | None) -> dict:
    """Set a profile value."""
    key = key.strip().lower()
    if not key:
        raise ValidationError("profile key cannot be empty")
    import json

    stored = json.dumps(value) if not isinstance(value, str) else value
    with get_conn() as c:
        existing = c.execute("SELECT id FROM user_profile WHERE key=?", (key,)).fetchone()
        if existing:
            c.execute(
                "UPDATE user_profile SET value=?, updated_at=? WHERE id=?",
                (stored, _now(), existing["id"]),
            )
        else:
            c.execute(
                "INSERT INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, stored, _now()),
            )
    return {"key": key, "value": value}


def get_profile(key: str | None = None) -> dict:
    """Get profile values. If key is None, return all."""
    import json

    with get_conn() as c:
        if key:
            row = c.execute("SELECT * FROM user_profile WHERE key=?", (key.strip().lower(),)).fetchone()
            if not row:
                raise NotFoundError(f"no profile key '{key}'", {"key": key})
            return _decode_row(dict(row))
        rows = c.execute("SELECT * FROM user_profile ORDER BY key").fetchall()
    return {"profile": [_decode_row(dict(r)) for r in rows]}


def _decode_row(row: dict) -> dict:
    import json

    value = row["value"]
    try:
        value = json.loads(value)
    except Exception:
        pass
    return {"key": row["key"], "value": value, "updated_at": row["updated_at"]}


def delete_profile(key: str) -> dict:
    with get_conn() as c:
        row = c.execute("SELECT * FROM user_profile WHERE key=?", (key.strip().lower(),)).fetchone()
        if not row:
            raise NotFoundError(f"no profile key '{key}'", {"key": key})
        c.execute("DELETE FROM user_profile WHERE key=?", (key.strip().lower(),))
    return {"deleted": row["key"]}
