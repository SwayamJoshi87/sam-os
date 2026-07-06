"""Schedule module — weekly template and today instances."""

from . import tools

MODULE = {
    "name": "schedule",
    "display_name": "Schedule",
    "description": "Weekly template and editable today schedule instances.",
    "tools": [
        tools.schedule_today,
        tools.schedule_week,
        tools.schedule_did,
        tools.schedule_skip,
        tools.schedule_push,
        tools.schedule_add_today,
        tools.schedule_remove_today,
        tools.schedule_retime_today,
        tools.schedule_diff_today_vs_template,
        tools.schedule_history,
        tools.schedule_stats,
        tools.category_add,
        tools.template_add,
        tools.template_remove,
        tools.template_update,
        tools.detect_conflicts,
        tools.schedule_resolve_conflict,
    ],
    "resources": [
        tools.schedule_today_resource,
    ],
    "scheduler_jobs": [],
}
