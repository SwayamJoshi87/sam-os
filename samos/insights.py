"""High-level summaries and composite resources for the MCP client."""

from __future__ import annotations

from datetime import datetime, timedelta

from .db import get_conn


def today_state() -> dict:
    """Composite snapshot of today: schedule, gym PRs, meals, wellness."""
    from .schedule import ensure_today, today_date
    from .gym import list_prs
    from .meals import today_meals
    from .wellness import water_today, sleep_history, mood_history, weight_history
    from .productivity import habits_today, is_away, shopping_list

    d = today_date()
    return {
        "date": d,
        "away": is_away(d),
        "schedule": ensure_today(),
        "gym_prs": list_prs(),
        "meals": today_meals(),
        "water": water_today(d),
        "sleep": sleep_history(7),
        "mood": mood_history(7),
        "weight": weight_history(7),
        "habits": habits_today(d),
        "shopping": shopping_list(),
    }


def weekly_prep() -> dict:
    """Sunday-style summary for the week ahead and week past."""
    from .schedule import stats as schedule_stats, template_week
    from .gym import list_prs
    from .meals import week_meals
    from .wellness import water_week, sleep_history, mood_history
    from .backup import backup_status

    last_week = schedule_stats(7)
    meals = week_meals()
    adherence = []
    for day in meals:
        target = day.get("target_calories") or 0
        cals = day.get("calories") or 0
        adherence.append(
            {
                "date": day["date"],
                "calories": cals,
                "target": target,
                "on_target": target > 0 and abs(cals - target) <= 0.1 * target,
            }
        )

    return {
        "generated_at": datetime.now().isoformat(),
        "upcoming_template": template_week(),
        "last_week_schedule": last_week,
        "last_week_meal_adherence": adherence,
        "current_prs": list_prs(),
        "last_week_water": water_week(7),
        "last_week_sleep": sleep_history(7),
        "last_week_mood": mood_history(7),
        "backup": backup_status(7),
    }
