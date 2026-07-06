"""MCP tool wrappers for the wellness module."""

from samos.db import _handle

from .models import (
    log_mood,
    log_sleep,
    log_water,
    mood_history,
    sleep_history,
    water_today,
    water_week,
    weight_history,
)


def water_log(amount_ml: int) -> dict:
    """Log water intake in millilitres for today."""
    return _handle(log_water, amount_ml)


def water_today_tool() -> dict:
    """Return today's water intake total and entries."""
    return _handle(water_today)


def water_week_tool(days: int = 7) -> dict:
    """Return daily water totals for the last N days."""
    return _handle(water_week, days)


def sleep_log(hours: float, quality: int | None = None, notes: str | None = None) -> dict:
    """Log last night's sleep. Quality is 1-10."""
    return _handle(log_sleep, hours, quality, notes)


def sleep_history_tool(days: int = 7) -> dict:
    """Return sleep history for the last N days."""
    return _handle(sleep_history, days)


def mood_log(level: int, label: str | None = None, note: str | None = None) -> dict:
    """Log mood level 1-10 with optional label and note."""
    return _handle(log_mood, level, label, note)


def mood_history_tool(days: int = 7) -> dict:
    """Return mood history for the last N days."""
    return _handle(mood_history, days)


def weight_history_tool(days: int = 30) -> dict:
    """Return weight entries from daily targets for the last N days."""
    return _handle(weight_history, days)
