"""MCP tools for user profile module."""

from __future__ import annotations

from samos.db import _handle

from .models import delete_profile, get_profile, set_profile


def profile_set(key: str, value: str) -> dict:
    """Set a profile key. Value can be JSON string for complex data."""
    import json

    try:
        parsed = json.loads(value)
    except Exception:
        parsed = value
    return _handle(set_profile, key, parsed)


def profile_get(key: str | None = None) -> dict:
    """Get profile value(s)."""
    return _handle(get_profile, key)


def profile_delete(key: str) -> dict:
    """Delete a profile key."""
    return _handle(delete_profile, key)
