"""MCP tool wrappers for the system module (setup, backup, health)."""

import json
import os

from samos import __version__
from samos.db import DB_PATH, schema_and_counts, _handle
from samos.modules.insights.models import weekly_prep

from .models import (
    backup_status as _backup_status,
    do_backup,
    run_setup as _run_setup,
    seed_template,
    setup_check,
    verify_calendar_credentials,
    write_hermes_config,
)


def setup_check_tool(use_docker: bool = False) -> dict:
    """Verify sam-os prerequisites: venv/docker, deps, DB path, credentials, config."""
    return _handle(setup_check, use_docker)


def setup_write_hermes_config(
    output_path: str | None = None,
    db_path: str | None = None,
    tz: str | None = None,
    calendar_offline: bool = False,
    use_docker: bool = False,
) -> dict:
    """Generate a Hermes mcp.json config for venv or Docker deployment."""
    return _handle(write_hermes_config, output_path, db_path, tz, calendar_offline, use_docker)


def setup_seed_template() -> dict:
    """Create a minimal starter weekly template if the template is empty."""
    return _handle(seed_template)


def setup_verify_calendar() -> dict:
    """Test iCloud CalDAV connectivity and return a clear report."""
    return _handle(verify_calendar_credentials)


def setup_run(
    write_hermes: bool = True,
    seed_template_flag: bool = True,
    calendar_offline: bool = False,
    use_docker: bool = False,
) -> dict:
    """Run full setup: check, write Hermes config, seed template, verify calendar."""
    return _handle(_run_setup, write_hermes, seed_template_flag, calendar_offline, use_docker)


def system_help() -> dict:
    """Return everything needed to operate sam-os: tools, schema, env, recovery."""
    from samos.registry import REGISTRY

    schema, counts = schema_and_counts()
    return {
        "ok": True,
        "data": {
            "service": {"name": "sam-os", "version": __version__, "db": str(DB_PATH)},
            "tools": sorted([t.__name__ for t in REGISTRY.all_tools()]),
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


def system_health() -> dict:
    """Return DB size, row counts, and scheduler/backup status."""
    data = {"db_path": str(DB_PATH), "db_exists": DB_PATH.exists()}
    if DB_PATH.exists():
        data["db_size_bytes"] = DB_PATH.stat().st_size
    schema, counts = schema_and_counts()
    data["row_counts"] = counts
    data["backup"] = _backup_status(7)
    data["calendar_offline"] = os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1"
    data["timezone"] = os.environ.get("TZ", "America/Toronto")
    return {"ok": True, "data": data}


def backup_status_tool(days: int = 7) -> dict:
    """Return recent backup run status."""
    return _handle(_backup_status, days)


def weekly_prep_tool() -> dict:
    """Return a Sunday-style summary: last week, upcoming template, PRs, backup status."""
    return _handle(weekly_prep)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def schema_resource() -> str:
    schema, counts = schema_and_counts()
    return json.dumps({"counts": counts, "tables": schema}, indent=2)


schema_resource._resource_name = "schema://tables"
