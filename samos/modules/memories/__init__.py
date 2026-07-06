"""Memories module for sam-os."""

from .tools import (
    memory_forget,
    memory_get,
    memory_recall,
    memory_remember,
    memory_update,
)

MODULE = {
    "name": "memories",
    "display_name": "Memories",
    "description": "Facts and preferences the agent should remember.",
    "tools": [
        memory_remember,
        memory_recall,
        memory_get,
        memory_update,
        memory_forget,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
