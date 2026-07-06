"""MCP tools for projects module."""

from __future__ import annotations

from samos.db import _handle

from .models import add_project, delete_project, get_project, list_projects, update_project


def project_add(name: str, description: str | None = None) -> dict:
    """Add a new project."""
    return _handle(add_project, name, description)


def project_list(status: str | None = None) -> dict:
    """List projects."""
    return _handle(list_projects, status)


def project_get(project_id: int) -> dict:
    """Get a project."""
    return _handle(get_project, project_id)


def project_update(project_id: int, name: str | None = None, description: str | None = None, status: str | None = None, notes: str | None = None) -> dict:
    """Update a project."""
    return _handle(update_project, project_id, name, description, status, notes)


def project_delete(project_id: int) -> dict:
    """Delete a project."""
    return _handle(delete_project, project_id)
