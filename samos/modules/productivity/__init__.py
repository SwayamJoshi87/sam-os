"""Productivity module — habits, shopping list, away mode, and task notes."""

from . import tools

MODULE = {
    "name": "productivity",
    "display_name": "Productivity",
    "description": "Habits, shopping list, away mode, and task notes.",
    "tools": [
        tools.habit_add,
        tools.habits_list,
        tools.habit_log,
        tools.habits_today_tool,
        tools.shopping_add,
        tools.shopping_list_tool,
        tools.shopping_mark_purchased,
        tools.shopping_clear_purchased,
        tools.away_mode_add,
        tools.away_mode_list,
        tools.away_mode_check,
        tools.task_note,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
