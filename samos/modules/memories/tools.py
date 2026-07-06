"""MCP tools for memories module."""

from __future__ import annotations

from samos.db import _handle

from .models import forget, get_memory, recall, remember, update_memory


def memory_remember(category: str, fact: str, confidence: int = 5, source: str | None = None) -> dict:
    """Store a fact the agent should remember."""
    return _handle(remember, category, fact, confidence, source)


def memory_recall(category: str | None = None, query: str | None = None, limit: int = 50) -> dict:
    """Recall stored facts, optionally filtered by category or query."""
    return _handle(recall, category, query, limit)


def memory_get(memory_id: int) -> dict:
    """Get a memory by id."""
    return _handle(get_memory, memory_id)


def memory_update(memory_id: int, fact: str | None = None, confidence: int | None = None, source: str | None = None) -> dict:
    """Update a memory."""
    return _handle(update_memory, memory_id, fact, confidence, source)


def memory_forget(memory_id: int) -> dict:
    """Delete a memory."""
    return _handle(forget, memory_id)
