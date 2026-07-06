"""Projects module for sam-os."""

from .tools import (
    project_add,
    project_delete,
    project_get,
    project_list,
    project_update,
)

MODULE = {
    "name": "projects",
    "display_name": "Projects",
    "description": "Long-running goals and work tracking.",
    "tools": [
        project_add,
        project_list,
        project_get,
        project_update,
        project_delete,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
