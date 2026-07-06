"""MCP tool wrappers for the schedule module."""

import json

from samos.db import _handle

from .models import (
    add_category,
    add_today_task,
    diff_today_vs_template,
    ensure_today,
    mark_done,
    mark_skip,
    push_task,
    remove_today_task,
    retime_today_task,
    stats as schedule_stats,
    template_add as _template_add,
    template_remove as _template_remove,
    template_reschedule,
    template_update as _template_update,
    template_week,
    week_history,
)


def schedule_today() -> dict:
    """Return today's living schedule. Auto-instantiates from template if missing."""
    return _handle(ensure_today)


def schedule_week() -> dict:
    """Return the weekly template."""
    return _handle(template_week)


def schedule_did(task_name: str) -> dict:
    """Mark today's pending instance of <task_name> as done."""
    return _handle(mark_done, task_name)


def schedule_skip(task_name: str, reason: str = "skipped") -> dict:
    """Mark today's pending instance of <task_name> as skipped."""
    return _handle(mark_skip, task_name, reason)


def schedule_push(task_name: str, day: str, permanent: bool = False) -> dict:
    """Move a task. One-off pushes to a future date; permanent rewrites the template."""
    if permanent:
        return _handle(template_reschedule, task_name, day)
    return _handle(push_task, task_name, day, permanent=False)


def schedule_add_today(task_name: str, category: str, time: str, duration_min: int) -> dict:
    """Add an ad-hoc task to today's living schedule without touching the weekly template."""
    return _handle(add_today_task, task_name, category, time, duration_min)


def schedule_remove_today(task_name_or_id: str, reason: str = "removed by user") -> dict:
    """Remove a task from today's living schedule."""
    try:
        val = int(task_name_or_id)
    except ValueError:
        val = task_name_or_id
    return _handle(remove_today_task, val, reason)


def schedule_retime_today(task_name_or_id: str, new_time: str) -> dict:
    """Change the time of a task already instantiated for today."""
    try:
        val = int(task_name_or_id)
    except ValueError:
        val = task_name_or_id
    return _handle(retime_today_task, val, new_time)


def schedule_diff_today_vs_template() -> dict:
    """Show how today's living schedule diverges from the weekly template."""
    return _handle(diff_today_vs_template)


def schedule_history(days: int = 7) -> dict:
    """Return schedule history for the last N days."""
    return _handle(week_history, days)


def schedule_stats(days: int = 7) -> dict:
    """Return completion stats by category for the last N days."""
    return _handle(schedule_stats, days)


def category_add(name: str, color: str = "#808080") -> dict:
    """Add a new schedule category."""
    return _handle(add_category, name, color)


def template_add(
    name: str,
    day: str,
    time_start: str,
    duration_min: int,
    category: str,
    fixed: bool = False,
) -> dict:
    """Add a recurring task to the weekly template."""
    return _handle(_template_add, name, day, time_start, duration_min, category, fixed)


def template_remove(task_name: str) -> dict:
    """Remove a recurring task from the weekly template."""
    return _handle(_template_remove, task_name)


def template_update(
    task_name: str,
    name: str | None = None,
    day: str | None = None,
    time_start: str | None = None,
    duration_min: int | None = None,
    category: str | None = None,
    fixed: bool | None = None,
) -> dict:
    """Update an existing recurring template task."""
    return _handle(
        _template_update,
        task_name,
        name,
        day,
        time_start,
        duration_min,
        category,
        fixed,
    )


def detect_conflicts() -> dict:
    """Detect schedule conflicts today and propose resolutions. Does not auto-apply."""
    from samos.calendar import detect_conflicts as calendar_detect_conflicts
    return _handle(calendar_detect_conflicts)


def schedule_resolve_conflict(task_name: str, option_index: int) -> dict:
    """Apply a proposed resolution from detect_conflicts."""
    from samos.calendar import resolve_conflict as calendar_resolve_conflict
    return _handle(calendar_resolve_conflict, task_name, option_index)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def schedule_today_resource() -> str:
    return json.dumps(ensure_today(), indent=2)


schedule_today_resource._resource_name = "schedule://today"
