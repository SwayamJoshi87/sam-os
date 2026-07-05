#!/usr/bin/env python3
"""Midnight cron — convert lingering pending instances to 'skipped'."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.schedule import end_of_day_sweep

n = end_of_day_sweep()
print(f"🌙 EOD sweep: {n} task(s) marked skipped (still pending at midnight)")
