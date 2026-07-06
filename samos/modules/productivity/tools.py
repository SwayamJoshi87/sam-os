"""MCP tool wrappers for the productivity module."""

from samos.db import _handle

from .models import (
    add_away_dates,
    add_habit as _add_habit,
    add_shopping_item,
    add_task_note,
    clear_purchased_items,
    habits_today,
    is_away,
    list_away_dates,
    list_habits,
    log_habit as _log_habit,
    mark_shopping_purchased,
    shopping_list as _shopping_list,
)


def habit_add(name: str, description: str | None = None) -> dict:
    """Create a new daily habit."""
    return _handle(_add_habit, name, description)


def habits_list() -> dict:
    """List all habits."""
    return _handle(list_habits)


def habit_log(habit_name: str, status: str, note: str | None = None) -> dict:
    """Mark a habit done or missed for today."""
    return _handle(_log_habit, habit_name, status, None, note)


def habits_today_tool() -> dict:
    """Return all habits and today's status."""
    return _handle(habits_today)


def shopping_add(item: str, category: str | None = None) -> dict:
    """Add an item to the shopping list."""
    return _handle(add_shopping_item, item, category)


def shopping_list_tool(show_purchased: bool = False) -> dict:
    """Return the shopping list."""
    return _handle(_shopping_list, show_purchased)


def shopping_mark_purchased(item_id: int, purchased: bool = True) -> dict:
    """Mark a shopping item as purchased or not."""
    return _handle(mark_shopping_purchased, item_id, purchased)


def shopping_clear_purchased() -> dict:
    """Remove all purchased shopping items."""
    return _handle(clear_purchased_items)


def away_mode_add(start_date: str, end_date: str, reason: str | None = None) -> dict:
    """Suppress schedule instantiation for a date range."""
    return _handle(add_away_dates, start_date, end_date, reason)


def away_mode_list() -> dict:
    """List all away-date ranges."""
    return _handle(list_away_dates)


def away_mode_check(date: str | None = None) -> dict:
    """Check whether a date falls inside an away range."""
    return _handle(is_away, date)


def task_note(task_name_or_id: str, note: str) -> dict:
    """Attach a note to today's instance of a task."""
    return _handle(add_task_note, task_name_or_id, note)
