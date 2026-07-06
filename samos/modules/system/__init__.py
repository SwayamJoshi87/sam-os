"""System module — setup, backup, and system health tools."""

from . import tools

MODULE = {
    "name": "system",
    "display_name": "System",
    "description": "Setup, backup, system health, and schema resources.",
    "tools": [
        tools.setup_check_tool,
        tools.setup_write_hermes_config,
        tools.setup_seed_template,
        tools.setup_verify_calendar,
        tools.setup_run,
        tools.system_help,
        tools.system_health,
        tools.backup_status_tool,
        tools.weekly_prep_tool,
    ],
    "resources": [
        tools.schema_resource,
    ],
    "scheduler_jobs": [],
}
