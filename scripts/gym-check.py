#!/usr/bin/env python3
"""8pm gym check — pings sam if today's gym instance is still pending."""
import sys
sys.path.insert(0, "/home/server/.hermes/scripts")
from schedule_lib import get_today_view, today_date

view = get_today_view()
gym_pending = [r for r in view if r["category"] == "gym" and r["status"] == "pending"]

if gym_pending:
    gym_name = gym_pending[0]["name"]
    time = gym_pending[0]["effective_time"]
    print(f"🏋️ gym check — {today_date()}. {gym_name} scheduled for {time}. did you do it? reply 'did gym' or 'skip gym <reason>'")
elif any(r["category"] == "gym" for r in view):
    # there was a gym task but it's done/skipped/moved
    print("✅ gym check — already logged today, nothing to ping")
else:
    print("")  # silent on non-gym days