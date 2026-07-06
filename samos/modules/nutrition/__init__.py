"""Nutrition module — meal logging and daily targets."""

from . import tools

MODULE = {
    "name": "nutrition",
    "display_name": "Nutrition",
    "description": "Meal logging, daily macro targets, and meal templates.",
    "tools": [
        tools.meal_log,
        tools.meal_target,
        tools.meals_today,
        tools.meals_week,
        tools.meal_template_add,
        tools.meal_templates_list,
        tools.meal_log_template,
    ],
    "resources": [
        tools.meals_today_resource,
    ],
    "scheduler_jobs": [],
}
