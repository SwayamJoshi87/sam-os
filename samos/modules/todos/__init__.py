"""Todos module for sam-os."""

from .tools import (
    todo_add,
    todo_cancel,
    todo_complete,
    todo_delete,
    todo_get,
    todo_list,
    todo_today,
    todo_update,
)

MODULE = {
    "name": "todos",
    "display_name": "Todos",
    "description": "Standalone action items and task list.",
    "tools": [
        todo_add,
        todo_list,
        todo_get,
        todo_complete,
        todo_cancel,
        todo_update,
        todo_delete,
        todo_today,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
