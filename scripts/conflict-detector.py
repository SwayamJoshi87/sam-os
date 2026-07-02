#!/usr/bin/env python3
"""Push-based: poll calendar, detect conflicts with today's schedule, ping if found."""
import sys, os, re
sys.path.insert(0, "/home/server/.hermes/scripts")
from datetime import datetime, timedelta
from pathlib import Path
from schedule_lib import get_today_view, today_date

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def _env(key):
    p = HERMES_HOME / ".env"
    if not p.exists():
        return ""
    for line in p.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip("\"'").strip()
    return ""


def get_calendar_events_today():
    """Returns list of (start_time, end_time, summary) for today's events."""
    try:
        from caldav import DAVClient
        import pytz
        email = "swayam.joshi1903@gmail.com"
        pwd = _env("ICLOUD_APP_PASSWORD")
        if not pwd:
            return []
        client = DAVClient(url="https://caldav.icloud.com/", username=email, password=pwd)
        principal = client.principal()
        calendars = principal.calendars()
        toronto = pytz.timezone('America/Toronto')
        today_start = datetime.now(toronto).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59)
        events = []
        for cal in calendars:
            try:
                results = cal.date_search(today_start, today_end)
                for e in results:
                    data = e.vcf_instance if hasattr(e, 'vcf_instance') else e.data
                    dtstart = re.search(r"DTSTART[^:]*[:=](.+?)(?:\r?\n|$)", data)
                    dtend = re.search(r"DTEND[^:]*[:=](.+?)(?:\r?\n|$)", data)
                    summary = re.search(r"^SUMMARY[:;](.+?)(?:\r?\n|$)", data, re.MULTILINE)
                    if dtstart and dtend:
                        s = dtstart.group(1).strip()
                        en = dtend.group(1).strip()

                        def parse(raw):
                            if "T" not in raw:
                                return None
                            d, t = raw.split("T")
                            return datetime.strptime(d + t[:6], "%Y%m%d%H%M%S")

                        ps = parse(s)
                        pe = parse(en)
                        name = summary.group(1).strip() if summary else "(untitled)"
                        if ps and pe:
                            events.append((ps, pe, name))
            except Exception:
                pass
        return events
    except Exception:
        return []


def detect_conflicts():
    view = get_today_view()
    events = get_calendar_events_today()
    if not events:
        return []
    conflicts = []
    for r in view:
        if r["status"] != "pending":
            continue
        try:
            task_start = datetime.combine(
                datetime.now().date(),
                datetime.strptime(r["effective_time"], "%H:%M").time()
            )
        except Exception:
            continue
        task_end = task_start + timedelta(minutes=r["duration_min"])
        for ev_start, ev_end, ev_name in events:
            if task_start < ev_end and task_end > ev_start:
                conflicts.append({
                    "task": r["name"],
                    "task_time": r["effective_time"],
                    "task_dur": r["duration_min"],
                    "event": ev_name,
                    "event_start": ev_start.strftime("%H:%M"),
                    "event_end": ev_end.strftime("%H:%M"),
                })
    return conflicts


if __name__ == "__main__":
    conflicts = detect_conflicts()
    if conflicts:
        lines = ["🚨 schedule conflicts detected:"]
        for c in conflicts:
            lines.append(f"   {c['task_time']} {c['task']} ({c['task_dur']}min) ↔ {c['event_start']}-{c['event_end']} {c['event']}")
            lines.append(f"     → reply 'move {c['task']} to <new time>' to reschedule")
        print("\n".join(lines))
    else:
        print("")