"""MCP resource wrappers for the insights module."""

import json

from .models import today_state


def state_today_resource() -> str:
    """Composite snapshot of today across all domains."""
    return json.dumps(today_state(), indent=2)


state_today_resource._resource_name = "state://today"
