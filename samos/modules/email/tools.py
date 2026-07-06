"""Email MCP tool wrappers."""

from samos.db import _handle
from samos.modules.email.models import daily_email_digest, read_email, search_emails, send_email, unread_emails


def email_unread(limit: int = 10):
    """Fetch unread emails from the configured inbox."""
    return _handle(unread_emails, limit=limit)


def email_search(query: str, limit: int = 20):
    """Search emails by subject or sender."""
    return _handle(search_emails, query=query, limit=limit)


def email_read(msg_id: str):
    """Read the full body of a specific email by msg_id."""
    return _handle(read_email, msg_id=msg_id)


def email_send(to: str, subject: str, body: str, html: bool = False):
    """Send an email via SMTP."""
    return _handle(send_email, to=to, subject=subject, body=body, html=html)


def email_daily_digest():
    """Get a summary of unread emails."""
    return _handle(daily_email_digest)
