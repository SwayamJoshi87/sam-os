"""MCP tools for the todos module."""

from __future__ import annotations

from samos.db import _handle

from .models import (
    add_todo,
    cancel_todo,
    complete_todo,
    delete_todo,
    get_todo,
    list_todos,
    todos_today,
    update_todo,
)


def todo_add(text: str, priority: int = 3, due_date: str | None = None, project_id: int | None = None, tags: str | None = None) -> dict:
    """Add a new todo."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return _handle(add_todo, text, priority, due_date, project_id, tag_list)


def todo_list(status: str | None = None, limit: int = 100) -> dict:
    """List todos."""
    return _handle(list_todos, status, limit)


def todo_get(todo_id: int) -> dict:
    """Get a single todo."""
    return _handle(get_todo, todo_id)


def todo_complete(todo_id: int) -> dict:
    """Mark a todo as done."""
    return _handle(complete_todo, todo_id)


def todo_cancel(todo_id: int) -> dict:
    """Cancel a todo."""
    return _handle(cancel_todo, todo_id)


def todo_update(todo_id: int, text: str | None = None, priority: int | None = None, due_date: str | None = None, project_id: int | None = None, tags: str | None = None) -> dict:
    """Update a todo."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return _handle(update_todo, todo_id, text, priority, due_date, project_id, tag_list)


def todo_delete(todo_id: int) -> dict:
    """Delete a todo."""
    return _handle(delete_todo, todo_id)


def todo_today() -> dict:
    """Return todos due today or overdue."""
    return _handle(todos_today)
