"""Insights module — composite today state and weekly prep summaries."""

from . import tools

MODULE = {
    "name": "insights",
    "display_name": "Insights",
    "description": "Composite today state and weekly prep summaries.",
    "tools": [],
    "resources": [
        tools.state_today_resource,
    ],
    "scheduler_jobs": [],
}
