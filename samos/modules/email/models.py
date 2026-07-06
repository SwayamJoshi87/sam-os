"""Email client domain logic (IMAP read + SMTP send)."""

from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from samos.db import ExternalError, ValidationError, get_conn


def _imap_conn():
    host = os.environ.get("EMAIL_IMAP_HOST")
    user = os.environ.get("EMAIL_IMAP_USER")
    pwd = os.environ.get("EMAIL_IMAP_PASSWORD")
    if not (host and user and pwd):
        raise ExternalError("email IMAP credentials not configured")
    try:
        conn = imaplib.IMAP4_SSL(host)
        conn.login(user, pwd)
        conn.select("INBOX")
        return conn
    except Exception as e:
        raise ExternalError(f"email IMAP connection failed: {e}")


def _smtp_conn():
    host = os.environ.get("EMAIL_SMTP_HOST")
    port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    user = os.environ.get("EMAIL_SMTP_USER") or os.environ.get("EMAIL_IMAP_USER")
    pwd = os.environ.get("EMAIL_SMTP_PASSWORD") or os.environ.get("EMAIL_IMAP_PASSWORD")
    if not (host and user and pwd):
        raise ExternalError("email SMTP credentials not configured")
    try:
        conn = smtplib.SMTP(host, port)
        conn.starttls()
        conn.login(user, pwd)
        return conn
    except Exception as e:
        raise ExternalError(f"email SMTP connection failed: {e}")


def _decode_header(value):
    parts = email.header.decode_header(value or "")
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _parse_message(raw_bytes: bytes, msg_id: str) -> dict:
    msg = email.message_from_bytes(raw_bytes)
    subject = _decode_header(msg.get("Subject", ""))
    from_ = _decode_header(msg.get("From", ""))
    date_str = msg.get("Date", "")
    try:
        date_parsed = email.utils.parsedate_to_datetime(date_str)
        date_iso = date_parsed.isoformat()
    except Exception:
        date_iso = date_str

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    return {
        "msg_id": msg_id,
        "subject": subject,
        "from": from_,
        "date": date_iso,
        "body": body[:2000],
    }


def unread_emails(limit: int = 10) -> list[dict]:
    """Fetch unread emails from INBOX."""
    conn = _imap_conn()
    try:
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            return []
        msg_ids = data[0].split()[-limit:]
        results = []
        for msg_id in msg_ids:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            parsed = _parse_message(msg_data[0][1], msg_id.decode())
            _cache_email(parsed)
            results.append(parsed)
        return results
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


def search_emails(query: str, limit: int = 20) -> list[dict]:
    """Search emails by subject/from."""
    conn = _imap_conn()
    try:
        status, data = conn.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
        if status != "OK":
            return []
        msg_ids = data[0].split()[-limit:]
        results = []
        for msg_id in msg_ids:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            parsed = _parse_message(msg_data[0][1], msg_id.decode())
            results.append(parsed)
        return results
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


def read_email(msg_id: str) -> dict:
    """Fetch full body of a specific email by msg_id."""
    conn = _imap_conn()
    try:
        status, msg_data = conn.fetch(msg_id.encode(), "(RFC822)")
        if status != "OK":
            raise ValidationError(f"could not fetch email {msg_id}")
        return _parse_message(msg_data[0][1], msg_id)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    """Send an email via SMTP."""
    user = os.environ.get("EMAIL_SMTP_USER") or os.environ.get("EMAIL_IMAP_USER")
    msg = MIMEText(body, "html" if html else "plain")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    conn = _smtp_conn()
    try:
        conn.send_message(msg)
    finally:
        conn.quit()
    return {"sent": True, "to": to, "subject": subject}


def daily_email_digest() -> dict:
    """Return a summary of unread emails."""
    emails = unread_emails(limit=20)
    summary = []
    for e in emails:
        line = f"- {e['from']}: {e['subject']}"
        summary.append(line)
    return {
        "count": len(emails),
        "summary": "\n".join(summary) if summary else "No unread emails.",
        "emails": emails,
    }


def _cache_email(parsed: dict):
    """Cache minimal metadata so agents can query without IMAP round-trip."""
    with get_conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO email_cache (msg_id, sender, subject, date, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (parsed["msg_id"], parsed["from"], parsed["subject"], parsed["date"], datetime.now().isoformat()),
        )
