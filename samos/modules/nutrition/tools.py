"""MCP tool wrappers for the nutrition module."""

import json

from samos.db import _handle
from samos.modules.schedule.models import today_date

from .models import (
    add_meal_template,
    get_day_meals,
    get_day_totals,
    get_target,
    list_meal_templates,
    log_meal,
    log_meal_template,
    set_target,
    today_meals,
    week_meals,
)


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


def meals_today() -> dict:
    """Return today's meals + totals vs target."""
    return _handle(today_meals)


def meals_week() -> dict:
    """Return last 7 days of meal adherence."""
    return _handle(week_meals)


def meal_template_add(
    name: str,
    meal_type: str,
    calories: float,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    description: str | None = None,
) -> dict:
    """Create a reusable meal template."""
    return _handle(add_meal_template, name, meal_type, calories, protein_g, carbs_g, fat_g, description)


def meal_templates_list() -> dict:
    """List all meal templates."""
    return _handle(list_meal_templates)


def meal_log_template(name: str) -> dict:
    """Log a meal from a template by name."""
    return _handle(log_meal_template, name)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def meals_today_resource() -> str:
    return json.dumps(today_meals(), indent=2)


meals_today_resource._resource_name = "meals://today"
