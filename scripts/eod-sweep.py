#!/usr/bin/env python3
"""Midnight cron — convert lingering pending instances to 'skipped'."""
import sys
sys.path.insert(0, "/home/server/.hermes/scripts")
from schedule_lib import end_of_day_sweep

n = end_of_day_sweep()
print(f"🌙 EOD sweep: {n} task(s) marked skipped (still pending at midnight)")