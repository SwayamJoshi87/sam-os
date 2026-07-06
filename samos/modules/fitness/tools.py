"""MCP tool wrappers for the fitness module."""

import json

from samos.db import ValidationError, _err, _handle

from .models import list_prs, log_workout, parse_workout, recent_workouts


def gym_log(gym: str, raw_text: str) -> dict:
    """Log a workout from free-form text like 'bench 135x10x3 squat 225x5'."""
    try:
        entries = parse_workout(raw_text)
        if not entries:
            return _err(ValidationError("could not parse workout", {"raw_text": raw_text}))
        return _handle(log_workout, gym, entries)
    except Exception as e:
        return _err(e)


def gym_prs(gym: str | None = None) -> dict:
    """List PRs. Filter by gym name if provided."""
    return _handle(list_prs, gym)


def gym_recent(days: int = 7) -> dict:
    """Return recent workouts for the last N days."""
    return _handle(recent_workouts, days)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def gym_prs_resource() -> str:
    return json.dumps(list_prs(), indent=2)


gym_prs_resource._resource_name = "gym://prs"
