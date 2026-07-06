"""User profile module for sam-os."""

from .tools import profile_delete, profile_get, profile_set

MODULE = {
    "name": "profile",
    "display_name": "User Profile",
    "description": "User preferences, goals, and identity data.",
    "tools": [
        profile_set,
        profile_get,
        profile_delete,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
