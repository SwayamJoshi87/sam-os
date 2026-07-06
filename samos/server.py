"""sam-os MCP server.

Runs as a stdio MCP server. Hermes launches this process and calls tools over
stdin/stdout. Internal cron jobs run on a background thread via APScheduler.
"""

from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from mcp.server.fastmcp import FastMCP

from . import __version__
from .calendar import detect_conflicts as calendar_detect_conflicts
from .calendar import sync_today_to_icloud
from .db import DB_PATH, SamosError, ValidationError, _err, _handle, init_db
from .modules.schedule.models import (
    dow_today,
    end_of_day_sweep,
    instantiate_day,
    stats as schedule_stats,
    today_date,
)
from .modules.system.models import do_backup
from .registry import REGISTRY


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
            from .modules.schedule.models import get_today_view
            n = instantiate_day(today_date(), dow_today(), source="cron")
            print(f"[scheduler] instantiated {n} task(s) for {today_date()}")
            if os.environ.get("SAMOS_CALENDAR_OFFLINE") != "1":
                result = sync_today_to_icloud()
                print(f"[scheduler] calendar sync: {result}")
        except Exception:
            traceback.print_exc()

    def gym_check_job():
        try:
            from .modules.schedule.models import get_today_view
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
# Register tools and resources from modules
# ---------------------------------------------------------------------------

for tool_fn in REGISTRY.all_tools():
    mcp.tool()(tool_fn)

for resource_fn in REGISTRY.all_resources():
    resource_name = getattr(resource_fn, "_resource_name", resource_fn.__name__)
    mcp.resource(resource_name)(resource_fn)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    init_db()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
