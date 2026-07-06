"""MCP tool wrappers for the agent interface."""

from samos.db import _handle
from samos.modules.agent.models import (
    agent_briefing,
    agent_context,
    agent_query,
    agent_remember,
    agent_search,
)


def agent_context_tool() -> dict:
    """Return a unified snapshot of the user's current moment (schedule, todos, meals, etc.)."""
    return _handle(agent_context)


def agent_query_tool(target: str) -> dict:
    """Look up a focused snapshot for a person, project, topic, or entity."""
    return _handle(agent_query, target=target)


def agent_search_tool(query: str) -> dict:
    """Search across todos, notes, memories, projects, schedule tasks, and graph entities."""
    return _handle(agent_search, query=query)


def agent_briefing_tool() -> dict:
    """Generate a concise daily briefing with schedule, todos, meals, conflicts, email, and weather."""
    return _handle(agent_briefing)


def agent_remember_tool(fact: str, entity_type: str = "memory", entity_name: str | None = None) -> dict:
    """Store a fact the agent should remember. Optionally tag it with an entity type/name."""
    return _handle(agent_remember, fact=fact, entity_type=entity_type, entity_name=entity_name)
