#!/usr/bin/env python3
"""Detect schedule conflicts today and print proposed resolutions."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.calendar import detect_conflicts

result = detect_conflicts()
if result["conflicts"]:
    print("🚨 schedule conflicts detected:")
    for c in result["conflicts"]:
        print(
            f"   {c['task_time']} {c['task']} ({c['task_dur']}min) ↔ "
            f"{c['conflict_start']}-{c['conflict_end']} {c['conflicts_with']}"
        )
        print("     proposed resolutions:")
        for i, p in enumerate(c["proposed_resolutions"]):
            print(f"       [{i}] {p['description']}")
        print("     → reply with the resolution index to apply it")
else:
    print("")
