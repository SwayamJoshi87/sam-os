"""Wellness tracking: water, sleep, mood, and weight trend."""

from __future__ import annotations

from datetime import datetime, timedelta

from .db import ValidationError, get_conn


def _date_str(d: datetime | None = None) -> str:
    return (d or datetime.now()).strftime("%Y-%m-%d")


def log_water(amount_ml: int, date: str | None = None) -> dict:
    """Log water intake in millilitres."""
    if amount_ml <= 0:
        raise ValidationError("amount_ml must be positive", {"value": amount_ml})
    d = date or _date_str()
    with get_conn() as c:
        c.execute(
            "INSERT INTO water_log (date, amount_ml) VALUES (?, ?)",
            (d, amount_ml),
        )
    return {"date": d, "amount_ml": amount_ml}


def water_today(date: str | None = None) -> dict:
    """Return today's water total and entries."""
    d = date or _date_str()
    with get_conn() as c:
        total = c.execute(
            "SELECT COALESCE(SUM(amount_ml), 0) AS total FROM water_log WHERE date=?",
            (d,),
        ).fetchone()["total"]
        entries = [
            dict(r)
            for r in c.execute(
                "SELECT id, amount_ml, logged_at FROM water_log WHERE date=? ORDER BY logged_at",
                (d,),
            ).fetchall()
        ]
    return {"date": d, "total_ml": total, "entries": entries}


def water_week(days: int = 7) -> list[dict]:
    """Return daily water totals for the last N days."""
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT date, COALESCE(SUM(amount_ml), 0) AS total_ml
            FROM water_log
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def log_sleep(hours: float, quality: int | None = None, notes: str | None = None, date: str | None = None) -> dict:
    """Log sleep for a date (default today)."""
    if hours <= 0 or hours > 24:
        raise ValidationError("hours must be between 0 and 24", {"value": hours})
    if quality is not None and not 1 <= quality <= 10:
        raise ValidationError("quality must be 1-10", {"value": quality})
    d = date or _date_str()
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO sleep_log (date, hours, quality, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET hours=excluded.hours,
                                            quality=excluded.quality,
                                            notes=excluded.notes,
                                            logged_at=CURRENT_TIMESTAMP
            """,
            (d, hours, quality, notes),
        )
    return {"date": d, "hours": hours, "quality": quality, "notes": notes}


def sleep_history(days: int = 7) -> list[dict]:
    """Return sleep history for the last N days."""
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM sleep_log WHERE date >= ? ORDER BY date",
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def log_mood(level: int, label: str | None = None, note: str | None = None, date: str | None = None) -> dict:
    """Log mood level 1-10 with optional label/note."""
    if not 1 <= level <= 10:
        raise ValidationError("mood level must be 1-10", {"value": level})
    d = date or _date_str()
    with get_conn() as c:
        c.execute(
            "INSERT INTO mood_log (date, level, label, note) VALUES (?, ?, ?, ?)",
            (d, level, label, note),
        )
    return {"date": d, "level": level, "label": label, "note": note}


def mood_history(days: int = 7) -> list[dict]:
    """Return mood history for the last N days."""
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM mood_log WHERE date >= ? ORDER BY date, logged_at",
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def weight_history(days: int = 30) -> list[dict]:
    """Return weight entries from daily_targets for the last N days."""
    since = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT date, weight_kg
            FROM daily_targets
            WHERE date >= ? AND weight_kg IS NOT NULL
            ORDER BY date
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]
