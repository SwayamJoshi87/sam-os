"""Notes and journal module for sam-os."""

from .tools import (
    journal_add,
    journal_get,
    journal_list,
    note_add,
    note_delete,
    note_get,
    note_list,
    note_search,
    note_update,
)

MODULE = {
    "name": "notes",
    "display_name": "Notes & Journal",
    "description": "Reference notes, ideas, and daily journal entries.",
    "tools": [
        note_add,
        note_search,
        note_list,
        note_get,
        note_update,
        note_delete,
        journal_add,
        journal_get,
        journal_list,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
