"""Wellness module — water, sleep, mood, and weight tracking."""

from . import tools

MODULE = {
    "name": "wellness",
    "display_name": "Wellness",
    "description": "Water, sleep, mood, and weight tracking.",
    "tools": [
        tools.water_log,
        tools.water_today_tool,
        tools.water_week_tool,
        tools.sleep_log,
        tools.sleep_history_tool,
        tools.mood_log,
        tools.mood_history_tool,
        tools.weight_history_tool,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
