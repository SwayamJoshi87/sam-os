#!/usr/bin/env python3
"""Apple Calendar (iCloud CalDAV) push writer.

Idempotent: writes one VEVENT per (date, task_id) with a stable UID, so re-runs
of the 8am cron update rather than duplicate events.

Reads credentials from ~/.hermes/.env:
  ICLOUD_APP_PASSWORD = <app-specific password>
  ICLOUD_USERNAME     = swayam.joshi1903@gmail.com (defaulted)

Usage:
  from apple_calendar import sync_today_to_icloud
  n = sync_today_to_icloud()           # syncs today's today_instances
  sync_today_to_icloud(dry_run=True)   # print what would happen, no writes
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

# icalendar / caldav imports — both installed in .venv
from icalendar import Calendar as ICalendar, Event, vText
from caldav import DAVClient

# Repo-local helpers (sqlite-backed schedule)
sys.path.insert(0, str(Path(__file__).parent))
from schedule_lib import get_today_view, today_date  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
ENV_PATH = HERMES_HOME / ".env"
CALDAV_URL = "https://caldav.icloud.com/"
DEFAULT_USERNAME = "swayam.joshi1903@gmail.com"
TARGET_CALENDAR_NAME = os.environ.get("SAMOS_CALENDAR", "sam-os")
TORONTO = ZoneInfo("America/Toronto")


def _env(key: str) -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip("\"'")
    return ""


def _creds() -> tuple[str, str]:
    user = _env("ICLOUD_USERNAME") or DEFAULT_USERNAME
    pwd = _env("ICLOUD_APP_PASSWORD")
    if not pwd:
        raise SystemExit(
            "ICLOUD_APP_PASSWORD missing in ~/.hermes/.env — get an "
            "app-specific password at https://appleid.apple.com/account/manage"
        )
    return user, pwd


# ---------------------------------------------------------------------------
# Client + calendar discovery
# ---------------------------------------------------------------------------


def _client() -> DAVClient:
    user, pwd = _creds()
    return DAVClient(url=CALDAV_URL, username=user, password=pwd)


def _find_or_create_calendar(client: DAVClient, name: str):
    """Find a calendar by display name. Create it if missing.

    Returns a caldav Calendar object. Matches by the CalDAV <displayname>
    property on the calendar collection, NOT by URL — same name across
    devices stays stable.
    """
    principal = client.principal()
    calendars = principal.calendars()
    for cal in calendars:
        try:
            display = cal.get_display_name()
        except Exception:
            display = None
        if display and display.strip().lower() == name.lower():
            return cal
    # Not found — create it via the principal
    new_cal = principal.make_calendar(name=name, cal_id=f"samos-{name.lower().replace(' ', '-')}")
    return new_cal


# ---------------------------------------------------------------------------
# Event building
# ---------------------------------------------------------------------------


def _uid(date_str: str, task_id: int) -> str:
    """Stable UID per (date, task_id). Re-runs overwrite instead of dup."""
    return f"samos-{date_str}-{task_id}@sam-os.local"


def _build_vevent(task: dict, date_str: str) -> Event:
    """Build an icalendar Event from a today_instances view row."""
    start_str = task.get("effective_time") or "09:00"
    h, m = (int(x) for x in start_str.split(":")[:2])
    start_local = datetime.fromisoformat(f"{date_str}T{start_str}").replace(tzinfo=TORONTO)
    end_local = start_local + timedelta(minutes=int(task.get("duration_min") or 30))

    ev = Event()
    ev.add("uid", _uid(date_str, task["task_id"]))
    ev.add("summary", task["name"])
    ev.add("dtstart", start_local)
    ev.add("dtend", end_local)
    ev.add("dtstamp", datetime.now(timezone.utc))

    # Category as a comma-separated list (RFC 5545)
    if task.get("category"):
        ev.add("categories", [task["category"]])

    desc_lines = [f"task_id={task['task_id']}", f"status={task.get('status', 'pending')}"]
    if task.get("color"):
        desc_lines.append(f"color={task['color']}")
    ev.add("description", "\n".join(desc_lines))

    # Status mapping
    status_map = {"done": "CONFIRMED", "skipped": "CANCELLED", "moved": "CANCELLED"}
    ev.add("status", status_map.get(task.get("status", "pending"), "TENTATIVE"))

    # TRANSP — show as busy/free based on category
    ev.add("transp", "OPAQUE" if task.get("fixed") else "TRANSPARENT")

    return ev


def _wrap_calendar(events: Iterable[Event]) -> ICalendar:
    cal = ICalendar()
    cal.add("prodid", "-//sam-os//apple_calendar.py//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    for ev in events:
        cal.add_component(ev)
    return cal


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_today_to_icloud(dry_run: bool = False) -> int:
    """Sync today's today_instances to the iCloud CalDAV calendar.

    Returns the number of events written/updated.
    Idempotent: same (date, task_id) → same UID → overwrites.
    """
    date_str = today_date()
    view = get_today_view()
    if not view:
        print(f"⚠ no today_instances for {date_str} — instantiate first")
        return 0

    if dry_run:
        for t in view:
            uid = _uid(date_str, t["task_id"])
            print(f"  [dry-run] {uid} → {t['effective_time']} {t['name']} ({t['status']})")
        print(f"✅ [dry-run] would sync {len(view)} event(s) for {date_str}")
        return len(view)

    client = _client()
    cal = _find_or_create_calendar(client, TARGET_CALENDAR_NAME)

    written = 0
    for t in view:
        ev = _build_vevent(t, date_str)
        ical_str = _wrap_calendar([ev]).to_ical().decode("utf-8")
        uid = _uid(date_str, t["task_id"])

        # Idempotency check — does this UID already exist on the calendar?
        existing = None
        try:
            existing = cal.event_by_uid(uid)
        except Exception:
            pass

        if existing:
            # Delete + recreate is the simplest cross-server-safe way to update
            existing.delete()
        cal.save_event(ical=ical_str)
        written += 1

    print(f"✅ synced {written} event(s) → icloud calendar '{TARGET_CALENDAR_NAME}' for {date_str}")
    return written


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    n = sync_today_to_icloud(dry_run=dry)
    sys.exit(0 if n >= 0 else 1)