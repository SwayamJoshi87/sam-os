#!/usr/bin/env python3
"""8am cron — instantiate today's schedule and optionally push to iCloud."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.calendar import sync_today_to_icloud
from samos.schedule import dow_today, instantiate_day, today_date


def main() -> int:
    date_str = today_date()
    dow = dow_today()
    n = instantiate_day(date_str, dow, source="cron")
    print(f"📋 instantiated {n} task(s) for {date_str} (dow={dow})")

    if os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1":
        print("⏭ calendar push skipped (SAMOS_CALENDAR_OFFLINE=1)")
        return 0

    try:
        result = sync_today_to_icloud()
        print(f"✅ calendar sync: {result}")
    except Exception as e:
        print(f"⚠ calendar push errored: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
