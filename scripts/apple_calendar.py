#!/usr/bin/env python3
"""Apple Calendar (iCloud CalDAV) push writer — CLI wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from samos.calendar import sync_today_to_icloud

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = sync_today_to_icloud(dry_run=dry)
    print(result)
