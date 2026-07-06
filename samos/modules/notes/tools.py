"""MCP tools for notes and journal."""

from __future__ import annotations

from samos.db import _handle

from .models import (
    add_journal_entry,
    add_note,
    delete_note,
    get_journal_entry,
    get_note,
    journal_history,
    list_notes,
    search_notes,
    update_note,
)


def note_add(title: str | None = None, body: str = "", tags: str | None = None) -> dict:
    """Add a note with optional tags (comma-separated)."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return _handle(add_note, title, body, tag_list)


def note_search(query: str, limit: int = 20) -> dict:
    """Search notes."""
    return _handle(search_notes, query, limit)


def note_list(limit: int = 50) -> dict:
    """List recent notes."""
    return _handle(list_notes, limit)


def note_get(note_id: int) -> dict:
    """Get a note by id."""
    return _handle(get_note, note_id)


def note_update(note_id: int, title: str | None = None, body: str | None = None, tags: str | None = None) -> dict:
    """Update a note."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return _handle(update_note, note_id, title, body, tag_list)


def note_delete(note_id: int) -> dict:
    """Delete a note."""
    return _handle(delete_note, note_id)


def journal_add(date: str, entry: str, mood: int | None = None) -> dict:
    """Add or update a journal entry for a date."""
    return _handle(add_journal_entry, date, entry, mood)


def journal_get(date: str) -> dict:
    """Get journal entry for a date."""
    return _handle(get_journal_entry, date)


def journal_list(days: int = 7) -> dict:
    """List recent journal entries."""
    return _handle(journal_history, days)
