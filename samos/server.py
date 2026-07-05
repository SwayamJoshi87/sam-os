"""sam-os MCP server.

Runs as a stdio MCP server. Hermes launches this process and calls tools over
stdin/stdout. Internal cron jobs run on a background thread via APScheduler.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from mcp.server.fastmcp import FastMCP

from . import __version__
from .backup import do_backup
from .calendar import detect_conflicts as calendar_detect_conflicts
from .calendar import resolve_conflict as calendar_resolve_conflict
from .calendar import sync_today_to_icloud
from .db import (
    DB_PATH,
    SamosError,
    ValidationError,
    init_db,
    schema_and_counts,
)
from .gym import list_prs as gym_list_prs
from .gym import log_workout as gym_log_workout
from .gym import parse_workout, recent_workouts
from .meals import get_day_meals, get_day_totals, get_target, log_meal, set_target, today_meals, week_meals
from .schedule import (
    add_today_task,
    diff_today_vs_template,
    ensure_today,
    end_of_day_sweep,
    mark_done,
    mark_skip,
    push_task,
    remove_today_task,
    retime_today_task,
    stats as schedule_stats,
    template_reschedule,
    template_week,
    today_date,
    week_history,
)


def _ok(data):
    return {"ok": True, "data": data}


def _err(e: Exception):
    if isinstance(e, SamosError):
        return {"ok": False, "error": {"type": e.error_type, "message": e.message, "details": e.details}}
    return {"ok": False, "error": {"type": "internal", "message": str(e), "details": {}}}


def _handle(fn, *args, **kwargs):
    try:
        return _ok(fn(*args, **kwargs))
    except Exception as e:
        traceback.print_exc()
        return _err(e)


INSTRUCTIONS = """You are sam-os, a personal operating system.

You have access to the user's schedule, gym log, and meals. Always prefer
calling tools over assuming state. The schedule has two layers:

- Template: the recurring weekly plan (schedule_week, template_reschedule).
- Today instances: the living schedule for the current day (schedule_today,
  schedule_add_today, schedule_remove_today, schedule_retime_today).

When the user says "something changed today", use the today-editing tools.
When the user wants a permanent recurring change, use template_reschedule.

Conflict detection (detect_conflicts) returns proposed resolutions. Never
apply a resolution without asking the user which option to choose.
"""


@asynccontextmanager
async def app_lifespan(app: FastMCP):
    scheduler = BackgroundScheduler(timezone=os.environ.get("TZ", "America/Toronto"))

    def instantiate_job():
        try:
            from .schedule import instantiate_day, dow_today
            n = instantiate_day(today_date(), dow_today(), source="cron")
            print(f"[scheduler] instantiated {n} task(s) for {today_date()}")
            if os.environ.get("SAMOS_CALENDAR_OFFLINE") != "1":
                result = sync_today_to_icloud()
                print(f"[scheduler] calendar sync: {result}")
        except Exception:
            traceback.print_exc()

    def gym_check_job():
        try:
            from .schedule import get_today_view
            view = get_today_view()
            pending = [r for r in view if r["category"] == "gym" and r["status"] == "pending"]
            if pending:
                print(f"[scheduler] gym check: {pending[0]['name']} at {pending[0]['effective_time']} pending")
            else:
                print("[scheduler] gym check: no pending gym task")
        except Exception:
            traceback.print_exc()

    def eod_sweep_job():
        try:
            n = end_of_day_sweep()
            print(f"[scheduler] EOD sweep: {n} task(s) marked skipped")
        except Exception:
            traceback.print_exc()

    def conflict_job():
        try:
            result = calendar_detect_conflicts()
            if result["conflicts"]:
                print(f"[scheduler] conflicts detected: {len(result['conflicts'])}")
                for c in result["conflicts"]:
                    print(f"  - {c['task']} @ {c['task_time']} ↔ {c['conflicts_with']}")
            else:
                print("[scheduler] no conflicts")
        except Exception:
            traceback.print_exc()

    def sunday_review_job():
        try:
            print("[scheduler] sunday review:")
            for r in schedule_stats(7):
                print(f"  {r}")
        except Exception:
            traceback.print_exc()

    def backup_job():
        try:
            do_backup()
        except Exception:
            traceback.print_exc()

    scheduler.add_job(instantiate_job, "cron", hour=8, minute=0)
    scheduler.add_job(gym_check_job, "cron", hour=20, minute=0)
    scheduler.add_job(eod_sweep_job, "cron", hour=0, minute=0)
    scheduler.add_job(conflict_job, "cron", minute="*/30", hour="8-20")
    scheduler.add_job(sunday_review_job, "cron", hour=20, minute=0, day_of_week="sun")
    scheduler.add_job(backup_job, "cron", hour=3, minute=0)
    scheduler.start()
    try:
        yield {"scheduler": scheduler}
    finally:
        scheduler.shutdown(wait=False)


mcp = FastMCP("sam-os", instructions=INSTRUCTIONS, lifespan=app_lifespan)


# ---------------------------------------------------------------------------
# Schedule tools
# ---------------------------------------------------------------------------

@mcp.tool()
def schedule_today() -> dict:
    """Return today's living schedule. Auto-instantiates from template if missing."""
    return _handle(ensure_today)


@mcp.tool()
def schedule_week() -> dict:
    """Return the weekly template."""
    return _handle(template_week)


@mcp.tool()
def schedule_did(task_name: str) -> dict:
    """Mark today's pending instance of <task_name> as done."""
    return _handle(mark_done, task_name)


@mcp.tool()
def schedule_skip(task_name: str, reason: str = "skipped") -> dict:
    """Mark today's pending instance of <task_name> as skipped."""
    return _handle(mark_skip, task_name, reason)


@mcp.tool()
def schedule_push(task_name: str, day: str, permanent: bool = False) -> dict:
    """Move a task. One-off pushes to a future date; permanent rewrites the template."""
    if permanent:
        return _handle(template_reschedule, task_name, day)
    return _handle(push_task, task_name, day, permanent=False)


@mcp.tool()
def schedule_add_today(task_name: str, category: str, time: str, duration_min: int) -> dict:
    """Add an ad-hoc task to today's living schedule without touching the weekly template."""
    return _handle(add_today_task, task_name, category, time, duration_min)


@mcp.tool()
def schedule_remove_today(task_name_or_id: str, reason: str = "removed by user") -> dict:
    """Remove a task from today's living schedule."""
    try:
        val = int(task_name_or_id)
    except ValueError:
        val = task_name_or_id
    return _handle(remove_today_task, val, reason)


@mcp.tool()
def schedule_retime_today(task_name_or_id: str, new_time: str) -> dict:
    """Change the time of a task already instantiated for today."""
    try:
        val = int(task_name_or_id)
    except ValueError:
        val = task_name_or_id
    return _handle(retime_today_task, val, new_time)


@mcp.tool()
def schedule_diff_today_vs_template() -> dict:
    """Show how today's living schedule diverges from the weekly template."""
    return _handle(diff_today_vs_template)


@mcp.tool()
def schedule_history(days: int = 7) -> dict:
    """Return schedule history for the last N days."""
    return _handle(week_history, days)


@mcp.tool()
def schedule_stats(days: int = 7) -> dict:
    """Return completion stats by category for the last N days."""
    return _handle(schedule_stats, days)


# ---------------------------------------------------------------------------
# Conflict tools
# ---------------------------------------------------------------------------

@mcp.tool()
def detect_conflicts() -> dict:
    """Detect schedule conflicts today and propose resolutions. Does not auto-apply."""
    return _handle(calendar_detect_conflicts)


@mcp.tool()
def schedule_resolve_conflict(task_name: str, option_index: int) -> dict:
    """Apply a proposed resolution from detect_conflicts."""
    return _handle(calendar_resolve_conflict, task_name, option_index)


# ---------------------------------------------------------------------------
# Gym tools
# ---------------------------------------------------------------------------

@mcp.tool()
def gym_log(gym: str, raw_text: str) -> dict:
    """Log a workout from free-form text like 'bench 135x10x3 squat 225x5'."""
    try:
        entries = parse_workout(raw_text)
        if not entries:
            return _err(ValidationError("could not parse workout", {"raw_text": raw_text}))
        return _handle(gym_log_workout, gym, entries)
    except Exception as e:
        return _err(e)


@mcp.tool()
def gym_prs(gym: str | None = None) -> dict:
    """List PRs. Filter by gym name if provided."""
    return _handle(gym_list_prs, gym)


@mcp.tool()
def gym_recent(days: int = 7) -> dict:
    """Return recent workouts for the last N days."""
    return _handle(recent_workouts, days)


# ---------------------------------------------------------------------------
# Meal tools
# ---------------------------------------------------------------------------

@mcp.tool()
def meal_log(
    meal_type: str,
    calories: float,
    description: str | None = None,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
) -> dict:
    """Log a meal for today."""
    return _handle(log_meal, today_date(), meal_type, calories, description, protein_g, carbs_g, fat_g)


@mcp.tool()
def meal_target(
    calories: float,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    weight_kg: float | None = None,
    notes: str | None = None,
) -> dict:
    """Set today's calorie/macro target."""
    return _handle(set_target, today_date(), calories, protein_g, carbs_g, fat_g, weight_kg, notes)


@mcp.tool()
def meals_today() -> dict:
    """Return today's meals + totals vs target."""
    return _handle(today_meals)


@mcp.tool()
def meals_week() -> dict:
    """Return last 7 days of meal adherence."""
    return _handle(week_meals)


# ---------------------------------------------------------------------------
# System tools
# ---------------------------------------------------------------------------

@mcp.tool()
def system_help() -> dict:
    """Return everything needed to operate sam-os: tools, schema, env, recovery."""
    schema, counts = schema_and_counts()
    return {
        "ok": True,
        "data": {
            "service": {"name": "sam-os", "version": __version__, "db": str(DB_PATH)},
            "tools": sorted(mcp._tool_manager._tools.keys()),
            "row_counts": counts,
            "tables": schema,
            "conventions": {
                "timezone": os.environ.get("TZ", "America/Toronto"),
                "date_format": "YYYY-MM-DD",
                "day_of_week": "0=mon, 1=tue, 2=wed, 3=thu, 4=fri, 5=sat, 6=sun",
                "status_enum": ["pending", "done", "skipped", "moved"],
                "meal_type_enum": ["breakfast", "lunch", "dinner", "snack"],
                "pr_formula": "epley_1rm = weight * (1 + reps/30)",
            },
        }
    }


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("schema://tables")
def schema_resource() -> str:
    schema, counts = schema_and_counts()
    return json.dumps({"counts": counts, "tables": schema}, indent=2)


@mcp.resource("schedule://today")
def schedule_today_resource() -> str:
    return json.dumps(ensure_today(), indent=2)


@mcp.resource("gym://prs")
def gym_prs_resource() -> str:
    return json.dumps(gym_list_prs(), indent=2)


@mcp.resource("meals://today")
def meals_today_resource() -> str:
    return json.dumps(today_meals(), indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    init_db()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
