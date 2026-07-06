"""Agent interface: unified read-only views over the whole sam-os graph."""

from __future__ import annotations

import os
from datetime import datetime

from samos.db import ValidationError, get_conn
from samos.graph import add_observation, ensure_entity, get_observations, get_relationships, search_entities


def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _safe_call(fn, *args, **kwargs):
    """Run a helper and return either its result or a structured error placeholder."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"_error": str(e)}


def agent_context() -> dict:
    """Return a unified snapshot of the user's current moment."""
    from samos.modules.fitness.models import recent_workouts
    from samos.modules.notes.models import list_notes
    from samos.modules.nutrition.models import today_meals
    from samos.modules.schedule.models import get_today_view, today_date
    from samos.modules.todos.models import list_todos

    ctx = {
        "now": _now(),
        "today": today_date(),
        "schedule": _safe_call(get_today_view),
        "todos": _safe_call(list_todos, "pending", 20),
        "meals": _safe_call(today_meals),
        "workouts": _safe_call(recent_workouts, 7),
        "notes": _safe_call(list_notes, 5),
    }

    # Optional external modules: only call if the required env var is present.
    if os.environ.get("EMAIL_IMAP_HOST"):
        from samos.modules.email.models import daily_email_digest

        ctx["email_digest"] = _safe_call(daily_email_digest)
    else:
        ctx["email_digest"] = {"enabled": False, "note": "email not configured"}

    default_location = os.environ.get("DEFAULT_WEATHER_LOCATION")
    if os.environ.get("OPENWEATHER_API_KEY") and default_location:
        from samos.modules.weather.models import current_weather

        ctx["weather"] = _safe_call(current_weather, default_location)
    else:
        ctx["weather"] = {"enabled": False, "note": "weather not configured or DEFAULT_WEATHER_LOCATION unset"}

    return ctx


def agent_query(target: str) -> dict:
    """Return a focused snapshot for a person, project, topic, or entity."""
    target = target.strip()
    if not target:
        raise ValidationError("target cannot be empty")

    from samos.modules.memories.models import recall as memory_recall
    from samos.modules.notes.models import search_notes
    from samos.modules.projects.models import list_projects
    from samos.modules.todos.models import list_todos

    entities = search_entities(target, limit=10)
    enriched = []
    for e in entities:
        entity_id = e["id"]
        e = dict(e)
        e["observations"] = get_observations(entity_id, limit=20)
        e["relationships"] = get_relationships(entity_id, "both")
        enriched.append(e)

    # Search other modules
    notes = search_notes(target, limit=10)
    memories = memory_recall(query=target, limit=10)
    projects = [p for p in list_projects() if target.lower() in p["name"].lower() or (p.get("description") and target.lower() in p["description"].lower())]
    todos = [t for t in list_todos(limit=100) if target.lower() in t["text"].lower() or (t.get("tags") and target.lower() in t["tags"].lower())]

    return {
        "target": target,
        "entities": enriched,
        "notes": notes,
        "memories": memories,
        "projects": projects,
        "todos": todos,
    }


def agent_search(query: str) -> dict:
    """Cross-module substring search."""
    query = query.strip()
    if not query:
        raise ValidationError("query cannot be empty")

    from samos.modules.memories.models import recall as memory_recall
    from samos.modules.notes.models import search_notes
    from samos.modules.todos.models import list_todos

    results: dict = {
        "entities": search_entities(query, limit=10),
        "todos": [t for t in list_todos(limit=200) if query.lower() in t["text"].lower() or (t.get("tags") and query.lower() in t["tags"].lower())],
        "notes": search_notes(query, limit=10),
        "memories": memory_recall(query=query, limit=10),
        "projects": [],
        "schedule_tasks": [],
    }

    with get_conn() as c:
        results["projects"] = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM projects WHERE name LIKE ? OR description LIKE ? OR notes LIKE ? ORDER BY updated_at DESC LIMIT 10",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()
        ]
        results["schedule_tasks"] = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM tasks WHERE name LIKE ? ORDER BY day_of_week, time_start LIMIT 10",
                (f"%{query}%",),
            ).fetchall()
        ]

    return results


def agent_briefing() -> dict:
    """Generate a concise daily briefing for the user or an upstream agent."""
    from samos.calendar import detect_conflicts
    from samos.modules.fitness.models import recent_workouts
    from samos.modules.nutrition.models import today_meals
    from samos.modules.schedule.models import get_today_view, today_date
    from samos.modules.todos.models import list_todos

    schedule = get_today_view()
    pending_todos = list_todos("pending", 20)
    meals = today_meals()
    workouts = recent_workouts(7)
    conflicts = detect_conflicts()

    email = {"enabled": False}
    if os.environ.get("EMAIL_IMAP_HOST"):
        from samos.modules.email.models import daily_email_digest

        email = _safe_call(daily_email_digest)

    weather = {"enabled": False}
    default_location = os.environ.get("DEFAULT_WEATHER_LOCATION")
    if os.environ.get("OPENWEATHER_API_KEY") and default_location:
        from samos.modules.weather.models import current_weather

        weather = _safe_call(current_weather, default_location)

    # Build a short natural-language summary for convenience
    lines = [f"Daily briefing for {today_date()}"]
    lines.append(f"- Schedule: {len(schedule)} item(s), {len([s for s in schedule if s.get('status') == 'pending'])} pending")
    lines.append(f"- Todos: {len(pending_todos)} pending")
    lines.append(f"- Meals logged today: {meals.get('today_total', {}).get('meal_count', 0)}")
    lines.append(f"- Workouts last 7 days: {len(workouts)}")
    if isinstance(conflicts, dict) and conflicts.get("conflicts"):
        lines.append(f"- Conflicts detected: {len(conflicts['conflicts'])}")
    if email.get("enabled") is not False:
        lines.append(f"- Unread emails: {email.get('count', 0)}")
    if weather.get("enabled") is not False:
        lines.append(f"- Weather: {weather.get('description', 'unknown')}, {weather.get('temp', '?')}°")

    return {
        "date": today_date(),
        "summary": "\n".join(lines),
        "schedule": schedule,
        "pending_todos": pending_todos,
        "meals": meals,
        "workouts": workouts,
        "conflicts": conflicts,
        "email": email,
        "weather": weather,
    }


def agent_remember(fact: str, entity_type: str = "memory", entity_name: str | None = None) -> dict:
    """Store a fact the agent should remember. Writes to both the graph store and the memories table."""
    fact = fact.strip()
    if not fact:
        raise ValidationError("fact cannot be empty")

    from samos.modules.memories.models import remember as memory_remember

    name = entity_name or fact[:50]
    entity_id = ensure_entity("agent", entity_type, name, entity_key=name)
    obs = add_observation(entity_id, "fact", fact)
    memory = memory_remember(category=entity_type, fact=fact, confidence=5, source="agent_remember")

    return {
        "entity_id": entity_id,
        "observation_id": obs.get("rowid") if isinstance(obs, dict) else None,
        "memory_id": memory.get("id"),
        "fact": fact,
        "entity_type": entity_type,
        "entity_name": name,
    }
