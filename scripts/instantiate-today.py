#!/usr/bin/env python3
"""8am cron — copy today's template tasks into today_instances, then push them
to the iCloud CalDAV calendar (idempotent).

Runs as part of the hermes 8am-instantiate-today cron job. The morning
briefing cron (8am-briefing) runs alongside it — that one *reads* calendar
events; this one *writes* them.

Idempotency:
  - today_instances has UNIQUE(date, task_id) — re-runs noop
  - apple_calendar UIDs are stable per (date, task_id) — re-runs overwrite
    existing VEVENTs instead of duplicating

Failures in the calendar push are logged but do NOT block the cron — a flaky
iCloud shouldn't take down schedule instantiation. Set SAMOS_CALENDAR_OFFLINE=1
to skip the push entirely (e.g. during maintenance).
"""
import os
import sys

# Use the repo's venv explicitly so the cron picks up caldav + icalendar
REPO = "/home/server/sam-os"
sys.path.insert(0, os.path.join(REPO, "scripts"))

from schedule_lib import instantiate_day, today_date, dow_today  # noqa: E402


def main() -> int:
    date_str = today_date()
    dow = dow_today()

    # Step 1 — populate today_instances from template
    n = instantiate_day(date_str, dow, source="cron")
    print(f"📋 instantiated {n} task(s) for {date_str} (dow={dow})")

    # Step 2 — push to iCloud calendar (best-effort)
    if os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1":
        print("⏭ calendar push skipped (SAMOS_CALENDAR_OFFLINE=1)")
        return 0

    try:
        # Re-exec under the repo venv so caldav/icalendar are importable when
        # this script is invoked by hermes (which uses system python).
        import subprocess

        result = subprocess.run(
            [
                os.path.join(REPO, ".venv", "bin", "python"),
                os.path.join(REPO, "scripts", "apple_calendar.py"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "SAMOS_DB_PATH": "/home/server/data/schedule.db"},
        )
        if result.returncode == 0:
            # Propagate the syncer's stdout (it prints the success line)
            for line in result.stdout.splitlines():
                if line.strip():
                    print(line)
        else:
            print(f"⚠ calendar push failed (exit={result.returncode}):")
            for line in (result.stderr or result.stdout).splitlines():
                if line.strip():
                    print(f"  {line}")
            # Non-fatal — instance population already succeeded
    except Exception as e:  # noqa: BLE001 — best-effort, log and continue
        print(f"⚠ calendar push errored: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())