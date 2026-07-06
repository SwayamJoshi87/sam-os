from samos.modules.email.tools import (
    email_daily_digest,
    email_read,
    email_search,
    email_send,
    email_unread,
)

MODULE = {
    "name": "email",
    "display_name": "Email",
    "description": "Read and send email via IMAP/SMTP.",
    "required_env": ["EMAIL_IMAP_HOST", "EMAIL_IMAP_USER", "EMAIL_IMAP_PASSWORD", "EMAIL_SMTP_HOST"],
    "tools": [email_unread, email_search, email_read, email_send, email_daily_digest],
    "resources": [],
    "scheduler_jobs": [],
}
