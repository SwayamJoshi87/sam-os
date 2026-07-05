#!/usr/bin/env python3
"""8pm gym check — pings if today's gym instance is still pending."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.schedule import get_today_view, today_date

view = get_today_view()
gym_pending = [r for r in view if r["category"] == "gym" and r["status"] == "pending"]

if gym_pending:
    print(
        f"🏋️ gym check — {today_date()}. {gym_pending[0]['name']} scheduled for "
        f"{gym_pending[0]['effective_time']}. did you do it? reply 'did gym' or 'skip gym <reason>'"
    )
elif any(r["category"] == "gym" for r in view):
    print("✅ gym check — already logged today, nothing to ping")
else:
    print("")
