"""Fitness module — workout logging and PR tracking."""

from . import tools

MODULE = {
    "name": "fitness",
    "display_name": "Fitness",
    "description": "Workout logging and personal-record tracking.",
    "tools": [
        tools.gym_log,
        tools.gym_prs,
        tools.gym_recent,
    ],
    "resources": [
        tools.gym_prs_resource,
    ],
    "scheduler_jobs": [],
}
