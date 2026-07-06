"""Apple Calendar (iCloud CalDAV) read/write and conflict detection."""

from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from .db import NotFoundError, ValidationError, get_conn
from .schedule import get_today_view, today_date

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
ENV_PATH = HERMES_HOME / ".env"
CALDAV_URL = "https://caldav.icloud.com/"
DEFAULT_USERNAME = os.environ.get("ICLOUD_USERNAME", "")
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
    return user, pwd


def _client():
    try:
        from caldav import DAVClient
    except ImportError:
        raise RuntimeError("caldav package not installed")
    user, pwd = _creds()
    if not pwd:
        raise RuntimeError("ICLOUD_APP_PASSWORD missing in ~/.hermes/.env")
    return DAVClient(url=CALDAV_URL, username=user, password=pwd)


def _find_or_create_calendar(client, name: str):
    try:
        principal = client.principal()
        calendars = principal.calendars()
    except Exception as e:
        raise RuntimeError(f"cannot access iCloud principal: {e}")
    for cal in calendars:
        try:
            display = cal.get_display_name()
        except Exception:
            display = None
        if display and display.strip().lower() == name.lower():
            return cal
    return principal.make_calendar(name=name, cal_id=f"samos-{name.lower().replace(' ', '-')}")


def _uid(date_str: str, task_id: int) -> str:
    return f"samos-{date_str}-{task_id}@sam-os.local"


def _build_vevent(task: dict, date_str: str):
    try:
        from icalendar import Calendar as ICalendar, Event
    except ImportError:
        raise RuntimeError("icalendar package not installed")

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
    if task.get("category"):
        ev.add("categories", [task["category"]])
    desc_lines = [f"task_id={task['task_id']}", f"status={task.get('status', 'pending')}"]
    if task.get("color"):
        desc_lines.append(f"color={task['color']}")
    ev.add("description", "\n".join(desc_lines))
    status_map = {"done": "CONFIRMED", "skipped": "CANCELLED", "moved": "CANCELLED"}
    ev.add("status", status_map.get(task.get("status", "pending"), "TENTATIVE"))
    ev.add("transp", "OPAQUE" if task.get("fixed") else "TRANSPARENT")
    return ev


def _wrap_calendar(events: Iterable):
    try:
        from icalendar import Calendar as ICalendar
    except ImportError:
        raise RuntimeError("icalendar package not installed")
    cal = ICalendar()
    cal.add("prodid", "-//sam-os//samos.calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    for ev in events:
        cal.add_component(ev)
    return cal


def sync_today_to_icloud(dry_run: bool = False) -> dict:
    """Sync today's today_instances to the iCloud CalDAV calendar."""
    if os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1":
        return {"synced": 0, "note": "SAMOS_CALENDAR_OFFLINE=1"}

    date_str = today_date()
    view = get_today_view()
    if not view:
        return {"synced": 0, "note": "no today_instances"}

    if dry_run:
        return {"synced": len(view), "dry_run": True, "events": [
            {"uid": _uid(date_str, t["task_id"]), "time": t["effective_time"], "name": t["name"], "status": t["status"]}
            for t in view
        ]}

    client = _client()
    cal = _find_or_create_calendar(client, TARGET_CALENDAR_NAME)
    written = 0
    for t in view:
        ev = _build_vevent(t, date_str)
        ical_str = _wrap_calendar([ev]).to_ical().decode("utf-8")
        uid = _uid(date_str, t["task_id"])
        existing = None
        try:
            existing = cal.event_by_uid(uid)
        except Exception:
            pass
        if existing:
            existing.delete()
        cal.save_event(ical=ical_str)
        written += 1
    return {"synced": written, "calendar": TARGET_CALENDAR_NAME, "date": date_str}


def get_calendar_events_today() -> list[tuple[datetime, datetime, str]]:
    """Returns list of (start_time, end_time, summary) for today's events."""
    if os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1":
        return []

    try:
        from caldav import DAVClient
        import pytz
    except ImportError:
        return []

    user, pwd = _creds()
    if not pwd:
        return []

    try:
        client = DAVClient(url=CALDAV_URL, username=user, password=pwd)
        principal = client.principal()
        calendars = principal.calendars()
    except Exception:
        return []

    toronto = pytz.timezone("America/Toronto")
    today_start = datetime.now(toronto).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    events = []

    for cal in calendars:
        try:
            results = cal.date_search(today_start, today_end)
            for e in results:
                data = e.vcf_instance if hasattr(e, "vcf_instance") else e.data
                dtstart = re.search(r"DTSTART[^:]*[:=](.+?)(?:\r?\n|$)", data)
                dtend = re.search(r"DTEND[^:]*[:=](.+?)(?:\r?\n|$)", data)
                summary = re.search(r"^SUMMARY[:;](.+?)(?:\r?\n|$)", data, re.MULTILINE)
                if not (dtstart and dtend):
                    continue
                ps = _parse_ical_datetime(dtstart.group(1).strip())
                pe = _parse_ical_datetime(dtend.group(1).strip())
                name = summary.group(1).strip() if summary else "(untitled)"
                if ps and pe:
                    events.append((ps, pe, name))
        except Exception:
            pass
    return events


def _parse_ical_datetime(raw: str) -> datetime | None:
    if "T" not in raw:
        return None
    d, t = raw.split("T")
    try:
        return datetime.strptime(d + t[:6], "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _task_to_interval(task: dict) -> tuple[datetime, datetime] | None:
    try:
        task_start = datetime.combine(
            datetime.now().date(),
            datetime.strptime(task["effective_time"], "%H:%M").time(),
        )
    except Exception:
        return None
    task_end = task_start + timedelta(minutes=task["duration_min"])
    return task_start, task_end


def detect_conflicts() -> dict:
    """Detect schedule conflicts and propose resolutions."""
    view = get_today_view()
    events = get_calendar_events_today()

    # Build intervals from fixed sam-os tasks
    task_intervals = []
    for r in view:
        if r["status"] != "pending":
            continue
        interval = _task_to_interval(r)
        if interval:
            task_intervals.append((interval[0], interval[1], r, "sam-os"))

    # Build intervals from external calendar events
    for ev_start, ev_end, ev_name in events:
        task_intervals.append((ev_start, ev_end, {"name": ev_name, "source": "calendar"}, "calendar"))

    conflicts = []
    for i, (s1, e1, obj1, src1) in enumerate(task_intervals):
        for s2, e2, obj2, src2 in task_intervals[i + 1 :]:
            if src1 == src2 == "sam-os":
                # Two sam-os tasks overlap
                if s1 < e2 and e1 > s2:
                    conflicts.append(_make_conflict(obj1, s1, e1, obj2, s2, e2))
            elif src1 != src2:
                # sam-os vs calendar
                if s1 < e2 and e1 > s2:
                    conflicts.append(_make_conflict(obj1, s1, e1, obj2, s2, e2))

    for c in conflicts:
        c["proposed_resolutions"] = _propose_resolutions(c)
    return {"date": today_date(), "conflicts": conflicts}


def _make_conflict(a, a_start, a_end, b, b_start, b_end) -> dict:
    return {
        "task": a.get("name"),
        "task_time": a_start.strftime("%H:%M"),
        "task_dur": int((a_end - a_start).total_seconds() // 60),
        "conflicts_with": b.get("name", b),
        "conflict_start": b_start.strftime("%H:%M"),
        "conflict_end": b_end.strftime("%H:%M"),
    }


def _propose_resolutions(conflict: dict) -> list[dict]:
    """Generate candidate resolutions for a conflict."""
    proposals = []
    # Move earlier today (simple heuristic: 1h earlier)
    try:
        original = datetime.strptime(conflict["task_time"], "%H:%M")
        earlier = (original - timedelta(hours=1)).strftime("%H:%M")
        proposals.append({"type": "retime_today", "new_time": earlier, "description": f"Move to {earlier} today"})
    except Exception:
        pass
    # Move later today
    try:
        original = datetime.strptime(conflict["task_time"], "%H:%M")
        later = (original + timedelta(hours=1)).strftime("%H:%M")
        proposals.append({"type": "retime_today", "new_time": later, "description": f"Move to {later} today"})
    except Exception:
        pass
    # Move to tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    proposals.append({"type": "push", "target_date": tomorrow, "description": f"Push to tomorrow ({tomorrow})"})
    # Skip
    proposals.append({"type": "skip", "description": "Skip this task today"})
    return proposals


def resolve_conflict(task_name: str, option_index: int) -> dict:
    """Apply a proposed resolution."""
    from .schedule import mark_skip, move_task, retime_today_task

    result = detect_conflicts()
    for c in result["conflicts"]:
        if c["task"] == task_name or task_name.lower() in c["task"].lower():
            proposals = c["proposed_resolutions"]
            if option_index < 0 or option_index >= len(proposals):
                raise ValidationError(
                    f"invalid option_index {option_index}",
                    {"valid_range": f"0-{len(proposals)-1}"},
                )
            p = proposals[option_index]
            if p["type"] == "retime_today":
                return {"applied": "retime_today", **retime_today_task(task_name, p["new_time"])}
            elif p["type"] == "push":
                return {"applied": "push", **move_task(task_name, p["target_date"], reason="conflict resolution")}
            elif p["type"] == "skip":
                return {"applied": "skip", **mark_skip(task_name, reason="conflict resolution")}
    raise NotFoundError(f"no conflict found for task '{task_name}'", {"task": task_name})
